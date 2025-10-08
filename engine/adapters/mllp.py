"""Skeleton MLLP adapter for upcoming Phase 1 work."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import AsyncIterator, Mapping

from ..contracts import Adapter, Message
from ..registry import register_adapter


@dataclass
class MLLPAdapter(Adapter):
    """Placeholder adapter that will stream HL7 messages over MLLP."""

    name: str
    host: str
    port: int
    connect_timeout: float = 3.0
    preview_messages: Sequence[str] = field(default_factory=tuple)

    async def stream(self) -> AsyncIterator[Message]:
        """Yield demo messages until the live client is implemented."""

        for idx, payload in enumerate(self.preview_messages, start=1):
            await asyncio.sleep(0)
            yield Message(
                id=f"demo-{idx}",
                raw=payload.encode("utf-8"),
                meta={"adapter": "mllp", "host": self.host, "port": self.port},
            )
        if not self.preview_messages:
            raise NotImplementedError(
                "MLLPAdapter is a stub; configure 'preview_messages' for dry runs"
            )


@register_adapter("mllp")
def _mllp_adapter(config: Mapping[str, object]) -> Adapter:
    host = str(config.get("host") or "localhost")
    port = int(config.get("port") or 2575)
    timeout = float(config.get("timeout") or 3.0)
    preview = config.get("preview_messages") or ()
    if isinstance(preview, str):
        preview = (preview,)
    elif isinstance(preview, Sequence):
        preview = tuple(preview)
    else:
        preview = (str(preview),)
    return MLLPAdapter(
        name="mllp",
        host=host,
        port=port,
        connect_timeout=timeout,
        preview_messages=preview,
    )
