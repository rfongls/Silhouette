"""Profile management endpoints for engine modules."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, Field

from insights.store import get_store

router = APIRouter(tags=["engine-profiles"])


class ProfileCreateRequest(BaseModel):
    kind: str = Field(..., pattern=r"^(transform|deid|validate)$")
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=500)
    config: dict[str, Any] = Field(default_factory=dict)


class ProfileItem(BaseModel):
    id: int
    kind: str
    name: str
    description: str | None
    config: dict[str, Any]


class ProfileListResponse(BaseModel):
    items: list[ProfileItem]


@router.post("/api/engine/profiles", status_code=201)
def create_profile(payload: ProfileCreateRequest) -> dict[str, int]:
    store = get_store()
    try:
        record = store.create_profile(
            kind=payload.kind,
            name=payload.name.strip(),
            description=payload.description,
            config=payload.config,
        )
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="profile name already exists") from exc
    return {"id": record.id}


@router.get("/api/engine/profiles", response_model=ProfileListResponse)
def list_profiles(kind: str | None = None) -> ProfileListResponse:
    if kind and kind not in {"transform", "deid", "validate"}:
        raise HTTPException(status_code=400, detail="unknown profile kind")
    store = get_store()
    items = [
        ProfileItem(
            id=profile.id,
            kind=profile.kind,
            name=profile.name,
            description=profile.description,
            config=profile.config,
        )
        for profile in store.list_profiles(kind)
    ]
    return ProfileListResponse(items=items)


class ProfileUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=500)
    config: dict[str, Any] | None = None


@router.put("/api/engine/profiles/{profile_id}")
def update_profile(profile_id: int, payload: ProfileUpdateRequest) -> dict[str, bool]:
    store = get_store()
    updated = store.update_profile(
        profile_id,
        name=payload.name,
        description=payload.description,
        config=payload.config,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="profile not found")
    return {"ok": True}


@router.delete("/api/engine/profiles/{profile_id}")
def delete_profile(profile_id: int) -> dict[str, bool]:
    store = get_store()
    try:
        deleted = store.delete_profile(profile_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="profile not found")
    return {"ok": True}
