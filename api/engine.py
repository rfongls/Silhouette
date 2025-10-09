"""Engine V2 API endpoints."""

from __future__ import annotations

import engine.plugins  # noqa: F401  # ensure component registration
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from engine.contracts import Result
from engine.runtime import EngineRuntime
from engine.registry import dump_registry
from engine.spec import dump_pipeline_spec, load_pipeline_spec
from insights.store import get_store

router = APIRouter()

_ENGINE_VERSION = "phase1"


class PipelineValidateRequest(BaseModel):
    yaml: str = Field(..., description="Pipeline specification in YAML format")


class PipelineValidateResponse(BaseModel):
    spec: dict


class PipelineRunRequest(BaseModel):
    yaml: str = Field(..., description="Pipeline specification in YAML format")
    max_messages: int | None = Field(
        1, ge=0, description="Maximum number of messages to process during the run"
    )
    persist: bool = Field(
        True,
        description="Persist run results to the insights store (creates run + issues)",
    )


class PipelineRunResponse(BaseModel):
    run_id: int | None = Field(None, description="Run identifier when persisted")
    processed: int = Field(..., description="Number of messages processed")
    issues: dict[str, int] = Field(
        default_factory=dict,
        description="Issue counts grouped by severity",
    )
    spec: dict = Field(..., description="Normalized pipeline specification")


@router.get("/api/engine/health", tags=["engine"], name="engine_health")
def engine_health() -> dict[str, object]:
    return {"ok": True, "version": _ENGINE_VERSION, "feature": "engine-v2"}


@router.get("/api/engine/registry", tags=["engine"], name="engine_registry")
def engine_registry() -> dict[str, dict[str, str]]:
    """Expose registered engine components for diagnostics."""

    return dump_registry()


@router.post(
    "/api/engine/pipelines/validate",
    response_model=PipelineValidateResponse,
    tags=["engine"],
)
def validate_pipeline(payload: PipelineValidateRequest) -> PipelineValidateResponse:
    try:
        spec = load_pipeline_spec(payload.yaml)
    except Exception as exc:  # pragma: no cover - FastAPI handles conversion
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    registry = dump_registry()
    missing: list[str] = []
    if spec.adapter.type not in registry.get("adapters", {}):
        missing.append(f"adapter:{spec.adapter.type}")
    for operator in spec.operators:
        if operator.type not in registry.get("operators", {}):
            missing.append(f"operator:{operator.type}")
    for sink in spec.sinks:
        if sink.type not in registry.get("sinks", {}):
            missing.append(f"sink:{sink.type}")
    if missing:
        raise HTTPException(
            status_code=400,
            detail="Unknown components: " + ", ".join(sorted(missing)),
        )
    return PipelineValidateResponse(spec=dump_pipeline_spec(spec))


@router.post(
    "/api/engine/pipelines/run",
    response_model=PipelineRunResponse,
    tags=["engine"],
)
async def run_pipeline(payload: PipelineRunRequest) -> PipelineRunResponse:
    """Execute a pipeline spec using the in-process runtime."""

    try:
        spec = load_pipeline_spec(payload.yaml)
    except Exception as exc:  # pragma: no cover - FastAPI handles conversion
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    store = get_store() if payload.persist else None
    run_id: int | None = None
    persist_cb = None

    if store is not None:
        store.ensure_schema()
        run = store.start_run(spec.name)
        run_id = run.id

        async def persist_result(result: Result) -> None:
            store.record_result(run_id=run_id, result=result)

        persist_cb = persist_result

    runtime = EngineRuntime(spec, persist_result=persist_cb)
    results = await runtime.run(max_messages=payload.max_messages)

    issue_counts: dict[str, int] = {"error": 0, "warning": 0, "passed": 0}
    for result in results:
        for issue in result.issues:
            issue_counts[issue.severity] = issue_counts.get(issue.severity, 0) + 1

    return PipelineRunResponse(
        run_id=run_id,
        processed=len(results),
        issues=issue_counts,
        spec=dump_pipeline_spec(spec),
    )
