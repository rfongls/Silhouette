from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import EventSourceResponse
from pydantic import BaseModel, Field

from agent.orchestrator import (
    IntentPlan,
    PlanStep,
    execute as _execute,
    interpret as _interpret,
)
from insights.store import get_store
from insights.models import AgentActionRecord

router = APIRouter(tags=["agent"])


# ---------- Models ----------

class InterpretRequest(BaseModel):
    text: str = Field(..., min_length=1)

class InterpretResponse(BaseModel):
    intent: str
    params: Dict[str, Any]
    steps: List[Dict[str, Any]]

class PlanStepModel(BaseModel):
    action: str
    args: Dict[str, Any] = Field(default_factory=dict)

class ExecuteRequest(BaseModel):
    intent: str
    params: Dict[str, Any]
    dry_run: bool = False
    steps: Optional[List[PlanStepModel]] = None

class ExecuteResponse(BaseModel):
    plan: List[Dict[str, Any]]
    report: List[Dict[str, Any]]
    activity: Dict[str, Any]

class ActionInfo(BaseModel):
    id: int
    ts: datetime
    actor: str
    intent: str
    status: str
    params: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    endpoint_id: Optional[int] = None
    job_id: Optional[int] = None
    run_id: Optional[int] = None

class ActionListResponse(BaseModel):
    items: List[ActionInfo]


# ---------- Registry ----------

_REGISTRY = {
    "intents": [
        {"name": "create_inbound_listener", "params": ["name", "host", "port", "pipeline_id", "allow_cidrs[]"]},
        {"name": "create_outbound_target", "params": ["name", "host", "port"]},
        {"name": "start_endpoint", "params": ["name|endpoint_id"]},
        {"name": "stop_endpoint", "params": ["name|endpoint_id"]},
        {"name": "delete_endpoint", "params": ["name|endpoint_id"]},
        {"name": "send_mllp", "params": ["target_name", "hl7_text|file_b64"]},
        {"name": "run_pipeline", "params": ["pipeline_id|name", "persist:boolean"]},
        {"name": "enqueue_job", "params": ["pipeline_id|name", "kind=run|replay", "payload"]},
        {"name": "assist_preview", "params": ["pipeline_id|name", "lookback_days"]},
        {"name": "cancel_job", "params": ["job_id"]},
        {"name": "assist_anomalies", "params": ["pipeline_id|name", "recent_days", "baseline_days"]},
        {"name": "generate_messages", "params": ["count", "out_folder"]},
        {"name": "deidentify_folder", "params": ["in_folder", "out_folder", "pipeline_id|name"]},
    ]
}

@router.get("/api/agent/registry")
def registry() -> Dict[str, Any]:
    return _REGISTRY


# ---------- Interpret ----------

@router.post("/api/agent/interpret", response_model=InterpretResponse)
def interpret(payload: InterpretRequest) -> InterpretResponse:
    plan = _interpret(payload.text)
    return InterpretResponse(intent=plan.intent, params=plan.params, steps=[{"action": s.action, "args": s.args} for s in plan.steps])


# ---------- Execute ----------

@router.post("/api/agent/execute", response_model=ExecuteResponse)
async def execute(payload: ExecuteRequest) -> ExecuteResponse:
    store = get_store()
    params = dict(payload.params or {})
    if not payload.steps:
        raise HTTPException(status_code=400, detail="steps required; call interpret before execute")
    plan = IntentPlan(
        intent=payload.intent,
        params=params,
        steps=[PlanStep(action=step.action, args=dict(step.args)) for step in payload.steps],
    )
    result = await _execute(store, plan, actor="demo-agent", dry_run=payload.dry_run)
    return ExecuteResponse(**result)


# ---------- Activity listing ----------

@router.get("/api/agent/actions", response_model=ActionListResponse)
def actions(limit: int = 50) -> ActionListResponse:
    store = get_store()
    # simple listing newest first
    with store.session() as session:
        rows = session.query(AgentActionRecord).order_by(AgentActionRecord.id.desc()).limit(max(limit, 1)).all()
    items = [
        ActionInfo(
            id=r.id, ts=r.ts, actor=r.actor, intent=r.intent, status=r.status,
            params=r.params, result=r.result, error=r.error,
            endpoint_id=r.endpoint_id, job_id=r.job_id, run_id=r.run_id
        )
        for r in rows
    ]
    return ActionListResponse(items=items)


# ---------- SSE: Activity stream ----------

@router.get("/api/agent/actions/stream")
async def stream_actions(request: Request, since: int = 0):
    """Very simple polling-to-SSE bridge for demo purposes.
    In production, replace with DB notifications or broker.
    """
    store = get_store()
    last_id: int = max(0, since)

    async def gen():
        nonlocal last_id
        while True:
            if await request.is_disconnected():
                break
            with store.session() as session:
                q = session.query(AgentActionRecord).filter(AgentActionRecord.id > last_id).order_by(AgentActionRecord.id.asc()).limit(100)
                rows = q.all()
            for r in rows:
                last_id = r.id
                ev = {
                    "id": r.id,
                    "ts": r.ts.isoformat(),
                    "actor": r.actor,
                    "intent": r.intent,
                    "status": r.status,
                    "params": r.params,
                    "result": r.result,
                    "error": r.error,
                    "endpoint_id": r.endpoint_id,
                    "job_id": r.job_id,
                    "run_id": r.run_id,
                }
                yield f"event: action\ndata: {json.dumps(ev)}\n\n"
            await asyncio.sleep(1.0)

    return EventSourceResponse(gen(), media_type="text/event-stream")
