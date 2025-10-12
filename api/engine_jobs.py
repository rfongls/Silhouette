from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

try:  # pragma: no cover - pydantic v1 fallback
    from pydantic import ConfigDict  # type: ignore
except ImportError:  # pragma: no cover
    ConfigDict = None  # type: ignore

from insights.store import (
    DuplicateJobError,
    InsightsStore,
    JobRecord,
    QueueFullError,
    get_store,
)
from .types import JobKind

router = APIRouter(tags=["engine"])


class JobEnqueueRequest(BaseModel):
    pipeline_id: int = Field(..., ge=1)
    kind: JobKind = "run"
    payload: dict[str, Any] | None = None
    priority: int = Field(0, ge=-10, le=10)
    scheduled_at: datetime | None = None
    max_attempts: int = Field(3, ge=1, le=10)
    dedupe_key: str | None = Field(None, max_length=255)


class JobInfo(BaseModel):
    id: int
    pipeline_id: int
    kind: str
    status: str
    priority: int
    attempts: int
    max_attempts: int
    scheduled_at: datetime
    leased_by: str | None = None
    run_id: int | None = None
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime
    payload: dict[str, Any] | None = None

    if ConfigDict is not None:  # pragma: no cover - pydantic v2 path
        model_config = ConfigDict(from_attributes=True)  # type: ignore[misc]

    class Config:  # pragma: no cover - pydantic v1 path
        orm_mode = True


class JobListResponse(BaseModel):
    items: list[JobInfo]


def _store() -> InsightsStore:
    return get_store()


def _serialize_job(job: JobRecord) -> JobInfo:
    data = {
        "id": job.id,
        "pipeline_id": job.pipeline_id,
        "kind": job.kind,
        "status": job.status,
        "priority": job.priority,
        "attempts": job.attempts,
        "max_attempts": job.max_attempts,
        "scheduled_at": job.scheduled_at,
        "leased_by": job.leased_by,
        "run_id": job.run_id,
        "last_error": job.last_error,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "payload": job.payload,
    }
    if hasattr(JobInfo, "model_validate"):
        return JobInfo.model_validate(data)  # type: ignore[attr-defined]
    return JobInfo(**data)


def _job_payload(info: JobInfo) -> dict[str, Any]:
    if hasattr(info, "model_dump"):
        return info.model_dump()  # type: ignore[attr-defined]
    return info.dict()


@router.post("/api/engine/jobs", response_model=JobInfo)
def jobs_enqueue(payload: JobEnqueueRequest) -> JobInfo:
    store = _store()
    try:
        job = store.enqueue_job(
            pipeline_id=payload.pipeline_id,
            kind=payload.kind,
            payload=payload.payload,
            scheduled_at=payload.scheduled_at,
            priority=payload.priority,
            max_attempts=payload.max_attempts,
            dedupe_key=payload.dedupe_key,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DuplicateJobError as exc:
        payload = getattr(exc, "job_data", None)
        if payload is None:
            payload = _job_payload(_serialize_job(exc.job))
        payload = jsonable_encoder(payload)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "job already exists", "job": payload},
        ) from exc
    except QueueFullError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    return _serialize_job(job)


@router.get("/api/engine/jobs", response_model=JobListResponse)
def jobs_list(
    status: list[str] | None = Query(None, description="Filter by job status"),
    pipeline_id: int | None = Query(None, ge=1),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> JobListResponse:
    store = _store()
    allowed_status = {
        "queued",
        "leased",
        "running",
        "succeeded",
        "failed",
        "canceled",
        "dead",
    }
    if status:
        invalid = sorted({value for value in status if value not in allowed_status})
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "unknown status", "status": invalid},
            )
    jobs = store.list_jobs(status=status, pipeline_id=pipeline_id, limit=limit, offset=offset)
    items = [_serialize_job(job) for job in jobs]
    return JobListResponse(items=items)


@router.get("/api/engine/jobs/{job_id}", response_model=JobInfo)
def jobs_get(job_id: int) -> JobInfo:
    store = _store()
    job = store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    return _serialize_job(job)


@router.post("/api/engine/jobs/{job_id}/cancel", response_model=dict)
def jobs_cancel(job_id: int) -> dict[str, bool]:
    store = _store()
    job = store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    if job.status not in {"queued", "leased", "running"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="job not cancelable")
    canceled = store.cancel_job(job_id)
    return {"canceled": canceled}


@router.post("/api/engine/jobs/{job_id}/retry", response_model=dict)
def jobs_retry(job_id: int) -> dict[str, bool]:
    store = _store()
    job = store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    if job.status not in {"dead", "canceled"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="job not retryable")
    enqueued = store.retry_job(job_id, now=datetime.utcnow())
    return {"enqueued": enqueued}


@router.post("/api/engine/jobs/{job_id}/requeue", response_model=dict)
def jobs_requeue(job_id: int) -> dict[str, bool]:
    store = _store()
    job = store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    if job.status not in {"failed", "dead", "canceled"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="job not requeueable")
    queued = store.requeue_job(job_id, now=datetime.utcnow())
    return {"queued": queued}
