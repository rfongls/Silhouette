"""Engine V2 API endpoints."""

from __future__ import annotations

import engine.plugins  # noqa: F401  # ensure component registration
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

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


class PipelineInfo(BaseModel):
    id: int
    name: str
    description: str | None = None
    updated_at: str


class PipelineListResponse(BaseModel):
    items: list[PipelineInfo]


class PipelineSaveRequest(BaseModel):
    id: int | None = Field(None, description="Pipeline identifier to update")
    name: str = Field(..., min_length=1, max_length=200)
    yaml: str = Field(..., description="Pipeline specification in YAML format")
    description: str | None = Field(None, max_length=500)


class PipelineSaveResponse(BaseModel):
    id: int
    spec: dict


class PipelineGetResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    yaml: str
    spec: dict
    updated_at: str


class PipelineStoredRunRequest(BaseModel):
    max_messages: int | None = Field(1, ge=0)
    persist: bool = Field(True)


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


@router.get("/api/engine/pipelines", response_model=PipelineListResponse, tags=["engine"])
def pipelines_list() -> PipelineListResponse:
    store = get_store()
    items: list[PipelineInfo] = []
    for record in store.list_pipelines():
        updated = record.updated_at.isoformat() if record.updated_at else ""
        items.append(
            PipelineInfo(
                id=record.id,
                name=record.name,
                description=record.description,
                updated_at=updated,
            )
        )
    return PipelineListResponse(items=items)


@router.get(
    "/api/engine/pipelines/{pipeline_id}",
    response_model=PipelineGetResponse,
    tags=["engine"],
)
def pipelines_get(pipeline_id: int) -> PipelineGetResponse:
    store = get_store()
    record = store.get_pipeline(pipeline_id)
    if record is None:
        raise HTTPException(status_code=404, detail="pipeline not found")
    updated = record.updated_at.isoformat() if record.updated_at else ""
    return PipelineGetResponse(
        id=record.id,
        name=record.name,
        description=record.description,
        yaml=record.yaml,
        spec=record.spec,
        updated_at=updated,
    )


@router.post("/api/engine/pipelines", response_model=PipelineSaveResponse, tags=["engine"])
def pipelines_save(payload: PipelineSaveRequest) -> PipelineSaveResponse:
    if len(payload.yaml.encode("utf-8")) > 200 * 1024:
        raise HTTPException(status_code=413, detail="pipeline yaml too large (limit 200 KB)")

    try:
        spec = load_pipeline_spec(payload.yaml)
    except Exception as exc:  # pragma: no cover - FastAPI handles conversion
        raise HTTPException(status_code=400, detail=f"invalid pipeline yaml: {exc}") from exc

    store = get_store()
    spec_dict = dump_pipeline_spec(spec)
    try:
        record = store.save_pipeline(
            name=payload.name,
            description=payload.description,
            yaml=payload.yaml,
            spec=spec_dict,
            pipeline_id=payload.id,
        )
    except KeyError as exc:  # pipeline not found during update
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="pipeline name must be unique") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PipelineSaveResponse(id=record.id, spec=spec_dict)


@router.delete("/api/engine/pipelines/{pipeline_id}", tags=["engine"])
def pipelines_delete(pipeline_id: int) -> dict[str, bool]:
    store = get_store()
    deleted = store.delete_pipeline(pipeline_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="pipeline not found")
    return {"ok": True}


@router.post(
    "/api/engine/pipelines/{pipeline_id}/run",
    response_model=PipelineRunResponse,
    tags=["engine"],
)
async def pipelines_run_stored(
    pipeline_id: int, payload: PipelineStoredRunRequest
) -> PipelineRunResponse:
    store = get_store()
    record = store.get_pipeline(pipeline_id)
    if record is None:
        raise HTTPException(status_code=404, detail="pipeline not found")

    try:
        spec = load_pipeline_spec(record.yaml)
    except Exception as exc:  # pragma: no cover - stored specs should already be valid
        raise HTTPException(status_code=400, detail=f"invalid pipeline yaml: {exc}") from exc

    runtime = EngineRuntime(spec)
    results = await runtime.run(max_messages=payload.max_messages)

    issue_counts: dict[str, int] = {"error": 0, "warning": 0, "passed": 0}
    for result in results:
        for issue in result.issues:
            severity = issue.severity or "warning"
            issue_counts[severity] = issue_counts.get(severity, 0) + 1

    run_id: int | None = None
    if payload.persist:
        store.ensure_schema()
        run = store.start_run(spec.name)
        run_id = run.id
        for result in results:
            store.record_result(run_id=run_id, result=result)

    return PipelineRunResponse(
        run_id=run_id,
        processed=len(results),
        issues=issue_counts,
        spec=dump_pipeline_spec(spec),
    )
