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
from engine.runtime import EngineRuntime
from engine.spec import dump_pipeline_spec, load_pipeline_spec
from agent.fs_utils import (
    in_folder,
    out_folder,
    synthesize_hl7,
    walk_hl7_files,
    write_bytes,
)

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

async def execute(
    store: InsightsStore,
    plan: IntentPlan,
    *,
    actor: str = "demo-agent",
    dry_run: bool = False,
) -> Dict[str, Any]:
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

        def _resolve_pipeline_id(identifier: Any) -> int:
            if identifier is None:
                raise ValueError("pipeline identifier required")
            if isinstance(identifier, int):
                return identifier
            ident_str = str(identifier).strip()
            if not ident_str:
                raise ValueError("pipeline identifier required")
            if ident_str.isdigit():
                return int(ident_str)
            pipeline = store.get_pipeline_by_name(ident_str)
            if pipeline is None:
                raise ValueError(f"pipeline {ident_str!r} not found")
            return pipeline.id

        # Iterate steps
        summary: Optional[Dict[str, Any]] = None

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

                elif step.action == "delete_endpoint":
                    name = step.args.get("name")
                    ep = _endpoint_by_name(name) if name else None
                    if not ep:
                        raise ValueError(f"endpoint {name!r} not found")
                    manager = get_manager(store)
                    await manager.stop_endpoint(ep.id)
                    store.delete_endpoint(ep.id)
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
                    ident = step.args.get("pipeline") or step.args.get("pipeline_id")
                    persist = bool(step.args.get("persist"))
                    pid = _resolve_pipeline_id(ident)
                    # Enqueue run as background job for parity with UI:
                    job = store.enqueue_job(pipeline_id=pid, kind="run", payload={"persist": persist})
                    s["job_id"] = job.id
                    store.update_action(action.id, job_id=job.id)

                elif step.action == "enqueue_job":
                    args = dict(step.args)
                    if "pipeline" in args and "pipeline_id" not in args:
                        args["pipeline_id"] = _resolve_pipeline_id(args["pipeline"])
                        del args["pipeline"]
                    if "pipeline_id" in args:
                        args["pipeline_id"] = _resolve_pipeline_id(args["pipeline_id"])
                    job = store.enqueue_job(**args)
                    s["job_id"] = job.id
                    store.update_action(action.id, job_id=job.id)

                elif step.action == "assist_preview":
                    # keep light; actual calculation is done by existing Assist APIs
                    s["note"] = "assist_preview enqueued"

                elif step.action == "generate_messages":
                    count = int(step.args.get("count") or 0)
                    folder = str(step.args.get("out_folder") or "").strip()
                    if not folder:
                        raise ValueError("out_folder is required")
                    out_dir = out_folder(folder)
                    written = 0
                    for idx in range(count):
                        filename = f"gen_{idx + 1:04d}.hl7"
                        write_bytes(out_dir, filename, synthesize_hl7(idx + 1))
                        written += 1
                    s["written"] = written
                    s["out_folder"] = str(out_dir)
                    summary = {"written": written, "out_folder": str(out_dir)}

                elif step.action == "deidentify_folder":
                    in_rel = str(step.args.get("in_folder") or "").strip()
                    out_rel = str(step.args.get("out_folder") or "").strip()
                    pipeline_identifier = step.args.get("pipeline_id") or step.args.get("pipeline")
                    pipeline_id = _resolve_pipeline_id(pipeline_identifier)
                    src_root = in_folder(in_rel)
                    dst_root = out_folder(out_rel)

                    pipeline = store.get_pipeline(pipeline_id)
                    if pipeline is None:
                        raise ValueError(f"pipeline {pipeline_id} not found")
                    base_spec = load_pipeline_spec(pipeline.spec or pipeline.yaml)
                    base_dict = dump_pipeline_spec(base_spec)

                    ok = 0
                    failed = 0
                    for hl7_path in walk_hl7_files(src_root):
                        try:
                            payload = hl7_path.read_bytes()
                            spec_dict = dict(base_dict)
                            spec_dict["adapter"] = {
                                "type": "inline",
                                "config": {
                                    "message_b64": base64.b64encode(payload).decode("ascii"),
                                    "meta": {"source_path": str(hl7_path)},
                                },
                            }
                            spec = load_pipeline_spec(spec_dict)
                            runtime = EngineRuntime(spec)
                            results = await runtime.run(max_messages=1)
                            if not results:
                                raise RuntimeError("pipeline returned no results")
                            write_bytes(dst_root, hl7_path.name, results[0].message.raw)
                            ok += 1
                        except Exception:  # noqa: PERF203 - fine-grained logging optional
                            failed += 1
                    s["ok"] = ok
                    s["failed"] = failed
                    s["in_folder"] = str(src_root)
                    s["out_folder"] = str(dst_root)
                    summary = {
                        "ok": ok,
                        "failed": failed,
                        "out_folder": str(dst_root),
                        "in_folder": str(src_root),
                    }

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

        result_payload: Dict[str, Any] = {"report": report}
        if summary:
            result_payload["summary"] = summary
        store.update_action(action.id, status="succeeded", result=result_payload)
        return {"plan": [s.__dict__ for s in plan.steps], "report": report, "activity": {"action_id": action.id}}

    except Exception as exc:
        store.update_action(action.id, status="failed", error=str(exc))
        return {"plan": [s.__dict__ for s in plan.steps], "report": report, "activity": {"action_id": action.id}}
