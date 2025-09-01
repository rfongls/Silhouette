#!/usr/bin/env python3
"""
LLM Orchestrator Smoke Test

Uses an OpenAI-compatible endpoint (vLLM/Ollama) to:
  1) Ask the model to send an HL7 message (natural language)
  2) Model calls the draft_and_send tool (OpenAI Tools API) OR emits a JSON tool call
  3) We execute the tool locally (silhouette_core.skills.hl7_drafter.draft_and_send)
  4) We send the tool result back to the model for a short summary
Prints the ACK and exits 0 on AA, 1 otherwise.

Example:
  # Start your MLLP server and vLLM/Ollama first.
  python -m interfaces.hl7.mllp_server &
  vllm serve meta-llama/Meta-Llama-3-8B-Instruct --download-dir ./model_vault &

  # Then:
  python scripts/agent_llm_smoke.py \
    --base http://localhost:8000/v1 \
    --model meta-llama/Meta-Llama-3-8B-Instruct \
    --host 127.0.0.1 --port 2575 \
    --message "Please send a VXU for John Doe (CVX 208) to localhost:2575 and summarize the ACK."
"""
from __future__ import annotations
import os
import sys
import json
import argparse
import asyncio
from typing import Any, Dict, List

import requests

from silhouette_core.skills.hl7_drafter import draft_and_send  # our local tool

DEFAULT_BASE = os.getenv("OPENAI_API_BASE", "http://localhost:8000/v1")
DEFAULT_KEY = os.getenv("OPENAI_API_KEY", "not-needed-for-local")

TOOL_SPEC = [
    {
        "type": "function",
        "function": {
            "name": "draft_and_send",
            "description": "Draft HL7v2 from templates and send via MLLP; returns {'message','ack'}.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message_type": {
                        "type": "string",
                        "enum": [
                            "VXU^V04",
                            "RDE^O11",
                            "ORM^O01",
                            "OML^O21",
                            "ORU^R01:RAD",
                            "MDM^T02",
                            "ADT^A01",
                            "SIU^S12",
                            "DFT^P03",
                        ],
                    },
                    "data": {
                        "type": "object",
                        "description": "JSON fields used to fill the Jinja template; e.g. patient_id, cvx_code, given, family, dob.",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["message_type", "data", "host", "port"],
                "additionalProperties": True,
            },
        },
    }
]

def post_chat(base: str, key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = base.rstrip("/") + "/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    }
    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=300)
    r.raise_for_status()
    return r.json()

def try_parse_json(s: str) -> Dict[str, Any] | None:
    s = s.strip()
    if "```" in s:
        parts = s.split("```")
        for i in range(1, len(parts), 2):
            block = parts[i]
            block = block.split("\n", 1)[1] if block.lower().startswith("json\n") else block
            try:
                return json.loads(block)
            except Exception:
                pass
    try:
        return json.loads(s)
    except Exception:
        return None

async def run(args):
    system = (
        "You are a helpful assistant that can use a tool named draft_and_send to send HL7 v2 messages via MLLP.\n"
        "When appropriate, call the tool with the correct message_type, data, host, and port. "
        "If tool calling is unavailable, output ONLY a JSON object with keys: tool_name='draft_and_send' and arguments={...}."
    )

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": args.message},
    ]

    payload = {
        "model": args.model,
        "messages": messages,
        "tools": TOOL_SPEC,
        "tool_choice": "auto",
        "temperature": 0.1,
        "max_tokens": 512,
    }

    try:
        resp = post_chat(args.base, args.key, payload)
        choice = resp["choices"][0]["message"]
    except Exception as e:
        print(f"[ERROR] Chat request failed: {e}", file=sys.stderr)
        sys.exit(2)

    tool_calls = choice.get("tool_calls") or []
    if tool_calls:
        tc = tool_calls[0]
        fn = tc["function"]["name"]
        raw_args = tc["function"]["arguments"]
        try:
            fn_args = json.loads(raw_args)
        except Exception:
            fn_args = try_parse_json(raw_args)
        if fn != "draft_and_send" or not isinstance(fn_args, dict):
            print(f"[ERROR] Unexpected tool call: name={fn} args={raw_args}", file=sys.stderr)
            sys.exit(2)
        result = await draft_and_send(
            fn_args["message_type"],
            fn_args["data"],
            fn_args["host"],
            int(fn_args["port"]),
        )
        messages.append(
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": tc.get("id", "tool_0"),
                        "type": "function",
                        "function": {"name": "draft_and_send", "arguments": raw_args},
                    }
                ],
            }
        )
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tc.get("id", "tool_0"),
                "name": "draft_and_send",
                "content": json.dumps(result),
            }
        )
        final = post_chat(
            args.base,
            args.key,
            {"model": args.model, "messages": messages, "temperature": 0.1, "max_tokens": 256},
        )
        summary = final["choices"][0]["message"].get("content", "")
        print("=== SUMMARY ===")
        print(summary.strip() if summary else "(no summary)")
        print("\n=== ACK ===")
        print(result["ack"].strip())
        sys.exit(0 if "MSA|AA|" in result["ack"] else 1)

    content = choice.get("content", "")
    plan = try_parse_json(content)
    if not plan or plan.get("tool_name") != "draft_and_send":
        print(
            "[ERROR] Model did not produce a tool call or valid JSON fallback.\nContent was:\n" + content,
            file=sys.stderr,
        )
        sys.exit(2)
    args_obj = plan.get("arguments") or {}
    result = await draft_and_send(
        args_obj["message_type"],
        args_obj["data"],
        args_obj["host"],
        int(args_obj["port"]),
    )
    print("=== ACK ===")
    print(result["ack"].strip())
    sys.exit(0 if "MSA|AA|" in result["ack"] else 1)

def main():
    ap = argparse.ArgumentParser(description="LLM Orchestrator Smoke (tool calling)")
    ap.add_argument(
        "--base",
        default=DEFAULT_BASE,
        help="OpenAI-compatible API base (vLLM/Ollama), e.g. http://localhost:8000/v1",
    )
    ap.add_argument("--model", required=True, help="Model name as served by your endpoint")
    ap.add_argument(
        "--key",
        default=DEFAULT_KEY,
        help="API key if required (ignored by most local endpoints)",
    )
    ap.add_argument("--host", default="127.0.0.1", help="MLLP host for the tool to send to")
    ap.add_argument("--port", type=int, default=2575, help="MLLP port for the tool to send to")
    ap.add_argument(
        "--message",
        default="Please send a VXU for John Doe (CVX 208) to localhost:2575 and summarize the ACK.",
        help="Natural language request for the agent",
    )
    args = ap.parse_args()
    asyncio.run(run(args))

if __name__ == "__main__":
    main()
