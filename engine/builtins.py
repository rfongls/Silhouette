"""Minimal built-in components for local development and tests."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Mapping

from .contracts import Adapter, Issue, Message, Operator, Result, Sink
from .registry import register_adapter, register_operator, register_sink


@dataclass
class _SequenceAdapter(Adapter):
    name: str
    _messages: list[Message]

    async def stream(self) -> AsyncIterator[Message]:
        for msg in self._messages:
            await asyncio.sleep(0)
            yield msg


@register_adapter("sequence")
def _sequence_adapter(config: Mapping[str, Any]) -> Adapter:
    payloads = config.get("messages") or [
        {"id": "demo-1", "text": "Hello Engine"},
        {"id": "demo-2", "text": "Phase 0"},
    ]
    messages = []
    for item in payloads:
        if isinstance(item, Mapping):
            msg_id = str(item.get("id") or f"msg-{len(messages)+1}")
            raw = str(item.get("text", "")).encode("utf-8")
            meta = {k: v for k, v in item.items() if k not in {"id", "text"}}
        else:
            msg_id = f"msg-{len(messages)+1}"
            raw = str(item).encode("utf-8")
            meta = {}
        messages.append(Message(id=msg_id, raw=raw, meta=meta))
    return _SequenceAdapter(name="sequence", _messages=messages)


@dataclass
class _EchoOperator(Operator):
    name: str
    annotation: str | None = None

    async def process(self, msg: Message) -> Result:
        issues = []
        if self.annotation:
            issues.append(
                Issue(
                    severity="passed",
                    code="echo",
                    message=self.annotation,
                    value=msg.meta.get("preview") if msg.meta else None,
                )
            )
        return Result(message=msg, issues=issues)


@register_operator("echo")
def _echo_operator(config: Mapping[str, Any]) -> Operator:
    annotation = str(config.get("note")) if config.get("note") else None
    return _EchoOperator(name="echo", annotation=annotation)


@dataclass
class _MemorySink(Sink):
    name: str
    store: list[Result] = field(default_factory=list)

    async def write(self, result: Result) -> None:
        self.store.append(result)


_MEMORY_SINKS: list[_MemorySink] = []


@register_sink("memory")
def _memory_sink(config: Mapping[str, Any]) -> Sink:
    sink = _MemorySink(name=config.get("label") or "memory")
    _MEMORY_SINKS.append(sink)
    return sink


def get_memory_sinks() -> list[_MemorySink]:
    """Return captured in-memory sinks for diagnostics/tests."""

    return list(_MEMORY_SINKS)


def reset_memory_sinks() -> None:
    """Clear captured sink state."""

    _MEMORY_SINKS.clear()
