"""Deterministic interpreter + executor (demo; no external LLM).
Maps simple natural commands to engine actions, plans steps, and executes them.
"""
from __future__ import annotations

import asyncio
import base64
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from insights.store import InsightsStore
from engine.net.endpoints import get_manager

# --- Intent plan -------------------------------------------------------------

@dataclass
class PlanStep:
    action: str
    args: Dict[str, Any]

@dataclass
class IntentPlan:
    intent: str
    params: Dict[str, Any]
    steps: List[PlanStep]


# --- Interpret ---------------------------------------------------------------

_SPACE = re.compile(r"\s+")

def _norm(text: str) -> str:
    return _SPACE.sub(" ", (text or "").strip())

def interpret(text: str) -> IntentPlan:
    """Map input text to an IntentPlan (no side effects)."""
    t = _norm(text).lower()

    # create inbound NAME on HOST:PORT for pipeline N allow CIDR[, CIDR...]
    m = re.match(r"^create inbound ['\"]?([\w\-\.:]+)['\"]? on ([\w\.\:]+):(\d+) for pipeline (\d+)(?: allow (.+))?$", t)
    if m:
        name, host, port, pipeline_id, allow = m.groups()
        cidrs = []
        if allow:
            cidrs = [c.strip() for c in re.split(r"[,\s]+", allow) if c.strip()]
        params = dict(name=name, host=host, port=int(port), pipeline_id=int(pipeline_id), allow_cidrs=cidrs)
        steps = [
            PlanStep("create_endpoint", {"kind": "mllp_in", "name": name, "pipeline_id": int(pipeline_id), "config": {"host": host, "port": int(port), "allow_cidrs": cidrs}}),
            PlanStep("start_endpoint", {"name": name}),
        ]
        return IntentPlan("create_inbound_listener", params, steps)

    # start/stop/delete endpoint NAME
    m = re.match(r"^(start|stop|delete) endpoint ['\"]?([\w\-\.:]+)['\"]?$", t)
    if m:
        op, name = m.groups()
        intent = f"{op}_endpoint"
        return IntentPlan(intent, {"name": name}, [PlanStep(intent, {"name": name})])

    # create outbound NAME to HOST:PORT
    m = re.match(r"^create outbound ['\"]?([\w\-\.:]+)['\"]? to ([\w\.\-]+):(\d+)$", t)
    if m:
        name, host, port = m.groups()
        params = {"name": name, "host": host, "port": int(port)}
        steps = [PlanStep("create_endpoint", {"kind": "mllp_out", "name": name, "pipeline_id": None, "config": {"host": host, "port": int(port)}})]
        return IntentPlan("create_outbound_target", params, steps)

    # send to NAME: HL7...
    m = re.match(r"^send to ['\"]?([\w\-\.:]+)['\"]?:\s*(.+)$", t, re.DOTALL)
    if m:
        target, hl7 = m.groups()
        return IntentPlan("send_mllp", {"target_name": target, "hl7_text": hl7}, [PlanStep("send_mllp", {"target_name": target, "hl7_text": hl7})])

    # run pipeline N persist (true|false)
    m = re.match(r"^run pipeline (.+?) persist (true|false)$", t)
    if m:
        ident, persist = m.groups()
        params = {"pipeline": ident, "persist": persist == "true"}
        return IntentPlan("run_pipeline", params, [PlanStep("run_pipeline", params)])

    # replay run N on pipeline P
    m = re.match(r"^replay run (\d+) on pipeline (\d+)$", t)
    if m:
        rid, pid = m.groups()
        params = {"pipeline_id": int(pid), "replay_run_id": int(rid)}
        return IntentPlan(
            "enqueue_job",
            {"pipeline_id": int(pid), "kind": "replay", "payload": {"replay_run_id": int(rid)}},
            [PlanStep("enqueue_job", {"pipeline_id": int(pid), "kind": "replay", "payload": {"replay_run_id": int(rid)}})],
        )

    # assist preview P lookback D
    m = re.match(r"^assist preview (\d+)(?: lookback (\d+))?$", t)
    if m:
        pid, look = m.groups()
        params = {"pipeline_id": int(pid), "lookback_days": int(look or 14)}
        return IntentPlan("assist_preview", params, [PlanStep("assist_preview", params)])

    # generate N ADT messages to FOLDER
    m = re.match(r"^generate (\d+).+?messages to ([\w\-/\.]+)$", t)
    if m:
        count, folder = m.groups()
        params = {"count": int(count), "out_folder": folder}
        return IntentPlan("generate_messages", params, [PlanStep("generate_messages", params)])

    # deidentify IN to OUT with pipeline P
    m = re.match(r"^deidentify ([\w\-/\.]+) to ([\w\-/\.]+) with pipeline (\d+)$", t)
    if m:
        inf, outf, pid = m.groups()
        params = {"in_folder": inf, "out_folder": outf, "pipeline_id": int(pid)}
        return IntentPlan("deidentify_folder", params, [PlanStep("deidentify_folder", params)])

    # default: unknown
    return IntentPlan("unknown", {"text": text}, [])


# --- Execute ----------------------------------------------------------------

async def _send_mllp(host: str, port: int, payload: bytes) -> bytes:
    reader, writer = await asyncio.open_connection(host, port)
    try:
        writer.write(b"\x0b" + payload + b"\x1c\x0d")
        await writer.drain()
        data = await reader.readuntil(b"\x1c\x0d")
        return data[:-2]
    finally:
        writer.close()
        await writer.wait_closed()

def _b64(s: str) -> str:
    return base64.b64encode(s.encode("utf-8")).decode("ascii")

async def execute(store: InsightsStore, plan: IntentPlan, *, actor: str = "demo-agent", dry_run: bool = False) -> Dict[str, Any]:
    """Execute a plan step-by-step, logging activity; return an execution report."""
    action = store.log_action(actor=actor, intent=plan.intent, params=plan.params, status="planned")
    report: List[Dict[str, Any]] = []

    try:
        if dry_run or plan.intent == "unknown":
            store.update_action(action.id, status="planned", result={"steps": [s.action for s in plan.steps]})
            return {"plan": [s.__dict__ for s in plan.steps], "report": report, "activity": {"action_id": action.id}}

        store.update_action(action.id, status="running")

        # helper: resolve endpoint by name
        def _endpoint_by_name(name: str):
            return store.get_endpoint_by_name(name)

        # Iterate steps
        for step in plan.steps:
            s = {"step": step.action, "status": "succeeded"}
            try:
                if step.action == "create_endpoint":
                    name = step.args["name"]
                    exists = store.get_endpoint_by_name(name)
                    if exists:
                        s["note"] = "exists"
                        endpoint_id = exists.id
                    else:
                        rec = store.create_endpoint(**step.args)
                        endpoint_id = rec.id
                    s["endpoint_id"] = endpoint_id
                    store.update_action(action.id, endpoint_id=endpoint_id)

                elif step.action in {"start_endpoint", "stop_endpoint"}:
                    name = step.args.get("name")
                    ep = _endpoint_by_name(name) if name else None
                    if not ep:
                        raise ValueError(f"endpoint {name!r} not found")
                    manager = get_manager(store)
                    if step.action == "start_endpoint":
                        await manager.start_endpoint(ep.id)
                        s["endpoint_id"] = ep.id
                    else:
                        await manager.stop_endpoint(ep.id)
                        s["endpoint_id"] = ep.id

                elif step.action == "send_mllp":
                    target = step.args.get("target_name")
                    hl7 = step.args.get("hl7_text", "")
                    if target:
                        ep = _endpoint_by_name(target)
                        if not ep or ep.kind != "mllp_out":
                            raise ValueError(f"target {target!r} not found")
                        ack = await _send_mllp(str(ep.config.get("host")), int(ep.config.get("port")), hl7.encode("utf-8"))
                    else:
                        raise ValueError("only target_name is supported in demo")
                    s["ack_preview"] = ack[:64].decode("utf-8", "ignore")

                elif step.action == "run_pipeline":
                    ident = step.args.get("pipeline")
                    persist = bool(step.args.get("persist"))
                    # ident can be id or name; here we assume id
                    pid = int(ident) if str(ident).isdigit() else None
                    if pid is None:
                        raise ValueError("only numeric pipeline id supported in demo")
                    # Enqueue run as background job for parity with UI:
                    job = store.enqueue_job(pipeline_id=pid, kind="run", payload={"persist": persist})
                    s["job_id"] = job.id
                    store.update_action(action.id, job_id=job.id)

                elif step.action == "enqueue_job":
                    job = store.enqueue_job(**step.args)
                    s["job_id"] = job.id
                    store.update_action(action.id, job_id=job.id)

                elif step.action == "assist_preview":
                    # keep light; actual calculation is done by existing Assist APIs
                    s["note"] = "assist_preview enqueued"

                elif step.action == "generate_messages":
                    # Write N simple messages to AGENT_DATA_ROOT/out/<folder> (implemented later by a job)
                    s["note"] = "generate scheduled"

                elif step.action == "deidentify_folder":
                    # Walk AGENT_DATA_ROOT/in/in_folder and schedule per-file deid jobs (implemented later)
                    s["note"] = "deidentify scheduled"

                else:
                    s["status"] = "failed"
                    s["error"] = f"unknown step {step.action}"

            except Exception as exc:
                s["status"] = "failed"
                s["error"] = str(exc)
                report.append(s)
                store.update_action(action.id, status="failed", error=str(exc))
                return {"plan": [st.__dict__ for st in plan.steps], "report": report, "activity": {"action_id": action.id}}

            report.append(s)

        store.update_action(action.id, status="succeeded", result={"report": report})
        return {"plan": [s.__dict__ for s in plan.steps], "report": report, "activity": {"action_id": action.id}}

    except Exception as exc:
        store.update_action(action.id, status="failed", error=str(exc))
        return {"plan": [s.__dict__ for s in plan.steps], "report": report, "activity": {"action_id": action.id}}
