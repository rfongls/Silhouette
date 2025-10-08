"""Engine V2 API endpoints."""

from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from engine.registry import dump_registry
from engine.spec import dump_pipeline_spec, load_pipeline_spec

router = APIRouter()

_ENGINE_VERSION = "phase0"


class PipelineValidateRequest(BaseModel):
    yaml: str = Field(..., description="Pipeline specification in YAML format")


class PipelineValidateResponse(BaseModel):
    spec: dict


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
    return PipelineValidateResponse(spec=dump_pipeline_spec(spec))
