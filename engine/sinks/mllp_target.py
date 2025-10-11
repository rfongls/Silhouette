"""Sink that forwards messages to a configured MLLP target."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from engine.contracts import Result, Sink
from engine.registry import register_sink
from insights.store import InsightsStore

VT = b"\x0b"
FS_CR = b"\x1c\x0d"


async def _send(host: str, port: int, payload: bytes) -> None:
    reader, writer = await asyncio.open_connection(host, port)
    try:
        writer.write(VT + payload + FS_CR)
        await writer.drain()
        await reader.readuntil(FS_CR)
    finally:
        writer.close()
        await writer.wait_closed()


@dataclass
class MLLPTargetSink(Sink):
    name: str
    target_name: str

    async def write(self, result: Result) -> None:
        store = InsightsStore.from_env()
        target = store.get_endpoint_by_name(self.target_name)
        if target is None or target.kind != "mllp_out":
            raise RuntimeError(f"target {self.target_name!r} not found")
        host = str(target.config.get("host") or "").strip()
        port = int(target.config.get("port") or 0)
        if not host or port <= 0:
            raise RuntimeError("target missing host/port configuration")
        await _send(host, port, result.message.raw)


@register_sink("mllp_target")
def _factory(config: dict) -> Sink:
    target_name = config.get("target_name")
    if not isinstance(target_name, str) or not target_name.strip():
        raise ValueError("mllp_target sink requires target_name")
    return MLLPTargetSink(name="mllp_target", target_name=target_name.strip())
