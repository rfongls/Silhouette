"""Minimal MLLP client adapter for Engine V2."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import AsyncIterator, Mapping

from ..contracts import Adapter, Message
from ..registry import register_adapter

_VT = 0x0B
_FS = 0x1C
_CR = 0x0D
_FS_CR = bytes((_FS, _CR))


@dataclass
class MLLPAdapter(Adapter):
    """Stream HL7 payloads framed with the Minimal Lower Layer Protocol."""

    name: str
    host: str
    port: int
    connect_timeout: float = 3.0

    async def stream(self) -> AsyncIterator[Message]:
        reader: asyncio.StreamReader
        writer: asyncio.StreamWriter

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.connect_timeout,
            )
        except asyncio.TimeoutError as exc:  # pragma: no cover - connection failure
            raise ConnectionError(
                f"Timed out connecting to {self.host}:{self.port}"
            ) from exc

        buffer = bytearray()
        counter = 0

        try:
            while True:
                chunk = await reader.read(4096)
                if not chunk:
                    if buffer:
                        raise RuntimeError("Connection closed while awaiting frame terminator")
                    break
                buffer.extend(chunk)

                while True:
                    start_idx = buffer.find(_VT)
                    if start_idx == -1:
                        buffer.clear()
                        break
                    if start_idx > 0:
                        del buffer[: start_idx]
                    if not buffer or buffer[0] != _VT:
                        break
                    end_idx = buffer.find(_FS_CR)
                    if end_idx == -1:
                        break
                    frame = bytes(buffer[1:end_idx])
                    del buffer[: end_idx + len(_FS_CR)]
                    counter += 1
                    yield Message(
                        id=f"mllp-{counter}",
                        raw=frame,
                        meta={
                            "adapter": "mllp",
                            "host": self.host,
                            "port": self.port,
                        },
                    )
        except asyncio.CancelledError:
            raise
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:  # pragma: no cover - best effort close
                pass


@register_adapter("mllp")
def _mllp_adapter(config: Mapping[str, object]) -> Adapter:
    host = str(config.get("host") or "127.0.0.1")
    port = int(config.get("port") or 2575)
    timeout_key = "connect_timeout" if "connect_timeout" in config else "timeout"
    timeout = float(config.get(timeout_key) or 3.0)
    role = str(config.get("role") or "client").strip().lower()
    if role != "client":
        raise ValueError("Phase 1 MLLP adapter only supports the 'client' role")
    return MLLPAdapter(name="mllp", host=host, port=port, connect_timeout=timeout)
