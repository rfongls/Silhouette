"""Endpoint message inspection endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from insights.store import get_store

router = APIRouter(tags=["engine-messages"])


class MessageItem(BaseModel):
    id: int
    received_at: str
    raw_len: int
    processed_len: int


class MessageListResponse(BaseModel):
    items: list[MessageItem]


@router.get("/api/engine/messages", response_model=MessageListResponse)
def list_messages(
    endpoint_id: int = Query(..., ge=1),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> MessageListResponse:
    store = get_store()
    endpoint = store.get_endpoint(endpoint_id)
    if endpoint is None:
        raise HTTPException(status_code=404, detail="endpoint not found")
    messages = store.list_endpoint_messages(
        endpoint_id=endpoint_id, limit=limit, offset=offset
    )
    items = [
        MessageItem(
            id=msg.id,
            received_at=msg.received_at.isoformat(),
            raw_len=len(msg.raw or b""),
            processed_len=len(msg.processed or b""),
        )
        for msg in messages
    ]
    return MessageListResponse(items=items)
