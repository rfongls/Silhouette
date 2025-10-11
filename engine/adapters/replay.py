"""Replay adapter: re-stream messages from a prior persisted run."""
from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import TYPE_CHECKING, AsyncIterator

from ..contracts import Adapter, Message
from ..registry import register_adapter
from insights.models import MessageRecord  # type: ignore
from sqlalchemy import select

if TYPE_CHECKING:  # pragma: no cover - import for type checking only
    from insights.store import InsightsStore


def _try_b64_decode(text: str) -> bytes:
    """Decode payload saved by Insights (may be plain text or base64)."""

    try:
        return base64.b64decode(text, validate=True)
    except Exception:
        return text.encode("utf-8", errors="replace")


@dataclass
class ReplayAdapter(Adapter):
    """Streams messages that were persisted in a previous run."""

    name: str
    run_id: int
    max_messages: int | None = None

    async def stream(self) -> AsyncIterator[Message]:
        from insights.store import get_store  # local import to avoid circular dependency

        store: "InsightsStore" = get_store()
        count = 0
        with store.session() as session:
            query = (
                select(MessageRecord)
                .where(MessageRecord.run_id == self.run_id)
                .order_by(MessageRecord.id.asc())
            )
            for record in session.execute(query).scalars():
                raw = _try_b64_decode(record.payload or "")
                meta = dict(record.meta or {})
                meta.setdefault("replay", True)
                meta.setdefault("source_run_id", self.run_id)
                yield Message(id=str(record.message_id), raw=raw, meta=meta)
                count += 1
                if self.max_messages is not None and count >= self.max_messages:
                    break


@register_adapter("replay")
def _replay_adapter(config) -> Adapter:  # type: ignore[override]
    run_id = int(config.get("run_id"))
    max_messages_value = config.get("max_messages")
    max_messages = None
    if max_messages_value not in (None, ""):
        max_messages = int(max_messages_value)
    return ReplayAdapter(name="replay", run_id=run_id, max_messages=max_messages)
