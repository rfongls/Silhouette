"""Utilities to send HL7 messages over MLLP."""

from __future__ import annotations

import asyncio
import base64

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from insights.store import get_store

router = APIRouter(tags=["engine"])

VT = b"\x0b"
FS_CR = b"\x1c\x0d"


class MLLPSendRequest(BaseModel):
    host: str | None = None
    port: int | None = Field(None, ge=1, le=65535)
    target_name: str | None = Field(None, min_length=1, max_length=200)
    message_b64: str


class MLLPSendResponse(BaseModel):
    acked: bool
    ack_preview: str | None = None


async def _send_mllp(host: str, port: int, payload: bytes) -> bytes:
    reader, writer = await asyncio.open_connection(host, port)
    try:
        writer.write(VT + payload + FS_CR)
        await writer.drain()
        data = await reader.readuntil(FS_CR)
        return data[:-2]
    finally:
        writer.close()
        await writer.wait_closed()


@router.post("/api/engine/mllp/send", response_model=MLLPSendResponse)
async def send_mllp(payload: MLLPSendRequest) -> MLLPSendResponse:
    store = get_store()
    host: str | None = None
    port: int | None = None

    if payload.target_name:
        target = store.get_endpoint_by_name(payload.target_name)
        if target is None or target.kind != "mllp_out":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="target not found")
        host = str(target.config.get("host") or "").strip()
        port = int(target.config.get("port") or 0)
    else:
        host = payload.host
        port = payload.port

    if not host or port is None or port <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="host/port required")

    try:
        message = base64.b64decode(payload.message_b64)
    except Exception as exc:  # pragma: no cover - invalid payload
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid base64") from exc

    ack = await _send_mllp(host, int(port), message)
    preview = ack[:64].decode("utf-8", "ignore") if ack else None
    return MLLPSendResponse(acked=True, ack_preview=preview)
