"""Insights summary endpoints for Engine V2."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from insights.store import get_store

router = APIRouter()


@router.get("/api/insights/summary", tags=["engine"], name="insights_summary")
def insights_summary() -> dict[str, object]:
    store = get_store()
    try:
        store.ensure_schema()
        summary = store.summaries()
    except Exception as exc:  # pragma: no cover - FastAPI handles conversion
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return summary
