from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from insights.store import get_store
from engine.net.endpoints import get_manager

router = APIRouter(tags=["engine-failed"])


class FailedItem(BaseModel):
    id: int
    endpoint_id: int | None
    pipeline_id: int | None
    received_at: str
    error: str | None


class FailedList(BaseModel):
    items: list[FailedItem]


@router.get("/api/engine/failed", response_model=FailedList)
def list_failed(
    endpoint_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> FailedList:
    store = get_store()
    rows = store.list_failed_messages(endpoint_id=endpoint_id, limit=limit, offset=offset)
    items = [
        FailedItem(
            id=row.id,
            endpoint_id=row.endpoint_id,
            pipeline_id=row.pipeline_id,
            received_at=row.received_at.isoformat(),
            error=row.error,
        )
        for row in rows
    ]
    return FailedList(items=items)


@router.post("/api/engine/failed/{failed_id}/requeue")
async def requeue_failed(failed_id: int) -> dict[str, bool]:
    store = get_store()
    record = store.get_failed_message(failed_id)
    if record is None:
        raise HTTPException(status_code=404, detail="failed message not found")
    if record.endpoint_id is None:
        raise HTTPException(status_code=409, detail="no endpoint associated with failed message")

    manager = get_manager(store)
    try:
        await manager._process_incoming(  # pylint: disable=protected-access
            record.endpoint_id,
            record.raw,
            dict(record.meta or {}),
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    store.delete_failed_message(failed_id)
    return {"ok": True}


@router.delete("/api/engine/failed/{failed_id}")
def delete_failed(failed_id: int) -> dict[str, bool]:
    store = get_store()
    if not store.delete_failed_message(failed_id):
        raise HTTPException(status_code=404, detail="failed message not found")
    return {"deleted": True}
