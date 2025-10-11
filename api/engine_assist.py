from __future__ import annotations

from datetime import datetime
from typing import Any, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from engine.ml_assist import compute_anomalies, render_draft_yaml, suggest_allowlist
from insights.store import get_store

router = APIRouter(tags=["engine"])


class AssistPreviewRequest(BaseModel):
    pipeline_id: int = Field(..., ge=1)
    lookback_days: int = Field(14, ge=1, le=90)


class AssistPreviewResponse(BaseModel):
    allowlist: list[dict[str, Any]]
    severity_rules: list[dict[str, Any]]
    notes: list[str]
    draft_yaml: str


class AnomalyInfo(BaseModel):
    code: str
    segment: str | None
    count: int
    baseline: float
    deviation: float
    window_start: datetime
    window_end: datetime


class AnomalyListResponse(BaseModel):
    items: List[AnomalyInfo]


@router.post("/api/engine/assist/preview", response_model=AssistPreviewResponse)
def assist_preview(payload: AssistPreviewRequest) -> AssistPreviewResponse:
    store = get_store()
    try:
        suggestions = suggest_allowlist(
            store,
            payload.pipeline_id,
            now=datetime.utcnow(),
            lookback_days=payload.lookback_days,
        )
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    draft = render_draft_yaml(suggestions)
    return AssistPreviewResponse(
        allowlist=suggestions.allowlist,
        severity_rules=suggestions.severity_rules,
        notes=suggestions.notes,
        draft_yaml=draft,
    )


@router.get("/api/engine/assist/anomalies", response_model=AnomalyListResponse)
def assist_anomalies(
    pipeline_id: int = Query(..., ge=1),
    recent_days: int = Query(7, ge=1, le=60),
    baseline_days: int = Query(30, ge=7, le=120),
    min_rate: float = Query(0.1, ge=0.0, le=1000.0),
) -> AnomalyListResponse:
    store = get_store()
    try:
        anomalies = compute_anomalies(
            store,
            pipeline_id,
            now=datetime.utcnow(),
            recent_days=recent_days,
            baseline_days=baseline_days,
            min_rate=min_rate,
        )
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    items = [
        AnomalyInfo(
            code=anomaly.code,
            segment=anomaly.segment,
            count=anomaly.count,
            baseline=anomaly.baseline,
            deviation=anomaly.deviation,
            window_start=anomaly.window_start,
            window_end=anomaly.window_end,
        )
        for anomaly in anomalies
    ]
    return AnomalyListResponse(items=items)
