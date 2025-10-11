"""Adapter that emits a single message sourced from job payload."""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from typing import AsyncIterator

from engine.contracts import Adapter, Message
from engine.registry import register_adapter


@dataclass
class InlineAdapter(Adapter):
    name: str
    payload_b64: str
    meta: dict | None = None

    async def stream(self) -> AsyncIterator[Message]:
        raw = base64.b64decode(self.payload_b64)
        await asyncio.sleep(0)
        yield Message(id="inline-1", raw=raw, meta=self.meta or {})


@register_adapter("inline")
def _inline_factory(config: dict) -> Adapter:
    payload = config.get("message_b64")
    if not isinstance(payload, str) or not payload:
        raise ValueError("inline adapter requires message_b64")
    meta = config.get("meta") if isinstance(config.get("meta"), dict) else None
    return InlineAdapter(name="inline", payload_b64=payload, meta=meta)
