"""CRUD and lifecycle APIs for Engine network endpoints."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field, validator
from sqlalchemy.exc import IntegrityError

from engine.net.endpoints import get_manager
from insights.store import get_store

router = APIRouter(tags=["engine"])


class EndpointCreateRequest(BaseModel):
    kind: Literal["mllp_in", "mllp_out"]
    name: str = Field(..., min_length=1, max_length=200)
    pipeline_id: int | None = Field(None, ge=1)
    config: dict[str, Any]
    sink_kind: Literal["folder", "db"] = "folder"
    sink_config: dict[str, Any] = Field(default_factory=dict)

    @validator("sink_config", pre=True, always=True)
    def _ensure_sink_config_dict(cls, value: Any) -> dict[str, Any]:  # noqa: D401
        """Validate that the sink configuration is a JSON object/dict."""
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError("sink_config must be an object")
        return value


class EndpointInfo(BaseModel):
    id: int
    kind: str
    name: str
    pipeline_id: int | None
    status: str
    config: dict[str, Any]
    sink_kind: str
    sink_config: dict[str, Any]
    last_error: str | None


class EndpointListResponse(BaseModel):
    items: list[EndpointInfo]


@router.post("/api/engine/endpoints", status_code=status.HTTP_201_CREATED)
def create_endpoint(payload: EndpointCreateRequest) -> dict[str, int]:
    store = get_store()
    try:
        record = store.create_endpoint(
            kind=payload.kind,
            name=payload.name.strip(),
            pipeline_id=payload.pipeline_id,
            config=payload.config,
            sink_kind=payload.sink_kind,
            sink_config=payload.sink_config,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="endpoint name already exists") from exc
    return {"id": record.id}


@router.get("/api/engine/endpoints", response_model=EndpointListResponse)
def list_endpoints(kind: str | None = Query(None)) -> EndpointListResponse:
    store = get_store()
    kinds = None
    if kind:
        if kind not in {"mllp_in", "mllp_out"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unknown kind")
        kinds = [kind]
    items = [
        EndpointInfo(
            id=record.id,
            kind=record.kind,
            name=record.name,
            pipeline_id=record.pipeline_id,
            status=record.status,
            config=record.config,
            sink_kind=record.sink_kind,
            sink_config=record.sink_config,
            last_error=record.last_error,
        )
        for record in store.list_endpoints(kind=kinds)
    ]
    return EndpointListResponse(items=items)


@router.get("/api/engine/endpoints/{endpoint_id}", response_model=EndpointInfo)
def get_endpoint(endpoint_id: int) -> EndpointInfo:
    store = get_store()
    record = store.get_endpoint(endpoint_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="endpoint not found")
    return EndpointInfo(
        id=record.id,
        kind=record.kind,
        name=record.name,
        pipeline_id=record.pipeline_id,
        status=record.status,
        config=record.config,
        sink_kind=record.sink_kind,
        sink_config=record.sink_config,
        last_error=record.last_error,
    )


class EndpointUpdateRequest(BaseModel):
    pipeline_id: int | None = Field(None, ge=1)
    config: dict[str, Any] | None = None
    sink_kind: Literal["folder", "db"] | None = None
    sink_config: dict[str, Any] | None = None

    @validator("config")
    def _validate_config(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is not None and not isinstance(value, dict):
            raise ValueError("config must be an object")
        return value

    @validator("sink_config")
    def _validate_sink_config(
        cls, value: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        if value is not None and not isinstance(value, dict):
            raise ValueError("sink_config must be an object")
        return value


@router.put("/api/engine/endpoints/{endpoint_id}")
def update_endpoint(endpoint_id: int, payload: EndpointUpdateRequest) -> dict[str, bool]:
    store = get_store()
    record = store.get_endpoint(endpoint_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="endpoint not found")

    updates: dict[str, Any] = {}
    if "pipeline_id" in payload.__fields_set__:
        if payload.pipeline_id is not None:
            pipeline = store.get_pipeline(payload.pipeline_id)
            if pipeline is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pipeline not found")
        updates["pipeline_id"] = payload.pipeline_id
    if payload.config is not None:
        updates["config"] = payload.config
    if payload.sink_kind is not None:
        updates["sink_kind"] = payload.sink_kind
    if payload.sink_config is not None:
        updates["sink_config"] = payload.sink_config

    if updates:
        store.update_endpoint(endpoint_id, **updates)
    return {"ok": True}


@router.post("/api/engine/endpoints/{endpoint_id}/start")
async def start_endpoint(endpoint_id: int) -> dict[str, bool]:
    store = get_store()
    manager = get_manager(store)
    try:
        await manager.start_endpoint(endpoint_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return {"started": True}


@router.post("/api/engine/endpoints/{endpoint_id}/stop")
async def stop_endpoint(endpoint_id: int) -> dict[str, bool]:
    store = get_store()
    manager = get_manager(store)
    await manager.stop_endpoint(endpoint_id)
    return {"stopped": True}


@router.post("/api/engine/endpoints/{endpoint_id}/refresh")
async def refresh_endpoint(endpoint_id: int) -> dict[str, bool]:
    store = get_store()
    manager = get_manager(store)
    await manager.stop_endpoint(endpoint_id)
    await manager.start_endpoint(endpoint_id)
    return {"refreshed": True}


@router.delete("/api/engine/endpoints/{endpoint_id}")
async def delete_endpoint(endpoint_id: int) -> dict[str, bool]:
    store = get_store()
    manager = get_manager(store)
    await manager.stop_endpoint(endpoint_id)
    deleted = store.delete_endpoint(endpoint_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="endpoint not found")
    return {"deleted": True}
