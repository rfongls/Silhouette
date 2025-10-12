"""Pipeline builder endpoints for engine endpoints."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from insights.store import get_store

router = APIRouter(tags=["engine-pipelines"])


class PipelineCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=500)
    scope: Literal["engine", "endpoint"] = "engine"
    endpoint_id: int | None = Field(None, ge=1)
    steps: list[int] = Field(default_factory=list)


class PipelineItem(BaseModel):
    id: int
    name: str
    description: str | None
    scope: Literal["engine", "endpoint"]
    endpoint_id: int | None
    steps: list[dict[str, Any]]


class PipelineListResponse(BaseModel):
    items: list[PipelineItem]


@router.post("/api/engine/pipelines", status_code=201)
def create_pipeline(payload: PipelineCreateRequest) -> dict[str, int]:
    store = get_store()
    record = store.save_pipeline(
        name=payload.name.strip(),
        description=payload.description,
        yaml="",
        spec={},
        scope=payload.scope,
        endpoint_id=payload.endpoint_id,
    )
    if payload.steps:
        store.set_pipeline_steps(record.id, payload.steps)
    return {"id": record.id}


@router.get("/api/engine/pipelines", response_model=PipelineListResponse)
def list_pipelines() -> PipelineListResponse:
    store = get_store()
    items: list[PipelineItem] = []
    for record in store.list_pipelines():
        steps = store.list_pipeline_steps(record.id)
        items.append(
            PipelineItem(
                id=record.id,
                name=record.name,
                description=record.description,
                scope=getattr(record, "scope", "engine"),
                endpoint_id=getattr(record, "endpoint_id", None),
                steps=[
                    {
                        "id": step.id,
                        "order": step.step_order,
                        "profile_id": step.module_profile_id,
                        "kind": step.profile.kind,
                        "name": step.profile.name,
                    }
                    for step in steps
                ],
            )
        )
    return PipelineListResponse(items=items)


class PipelineUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=500)
    scope: Literal["engine", "endpoint"] | None = None
    endpoint_id: int | None = Field(None, ge=1)
    steps: list[int] | None = None


@router.put("/api/engine/pipelines/{pipeline_id}")
def update_pipeline(pipeline_id: int, payload: PipelineUpdateRequest) -> dict[str, bool]:
    store = get_store()
    record = store.get_pipeline(pipeline_id)
    if record is None:
        raise HTTPException(status_code=404, detail="pipeline not found")

    endpoint_update = record.endpoint_id
    if "endpoint_id" in payload.__fields_set__:
        endpoint_update = payload.endpoint_id

    updated = store.save_pipeline(
        name=payload.name or record.name,
        description=payload.description if payload.description is not None else record.description,
        yaml=record.yaml or "",
        spec=record.spec,
        pipeline_id=pipeline_id,
        scope=payload.scope if payload.scope is not None else record.scope,
        endpoint_id=endpoint_update,
    )
    if payload.steps is not None:
        store.set_pipeline_steps(updated.id, payload.steps)
    return {"ok": True}
