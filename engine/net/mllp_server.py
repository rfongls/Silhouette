"""Minimal MLLP server for inbound HL7 ingest."""

from __future__ import annotations

import asyncio
import base64
import ipaddress
import logging
import os
from dataclasses import dataclass, field
from typing import Iterable

from insights.store import InsightsStore, QueueFullError

logger = logging.getLogger(__name__)

VT = b"\x0b"
FS_CR = b"\x1c\x0d"

_READ_TIMEOUT_SECS = max(float(os.getenv("ENGINE_MLLP_READ_TIMEOUT_SECS", "30")), 0.1)
_MAX_FRAME_BYTES = max(int(os.getenv("ENGINE_MLLP_MAX_FRAME_BYTES", "1000000")), 1)


def _allowed(peer_ip: str, cidrs: Iterable[str]) -> bool:
    """Return ``True`` when ``peer_ip`` is contained in one of ``cidrs``."""

    try:
        ip = ipaddress.ip_address(peer_ip)
    except ValueError:
        return False

    for raw in cidrs:
        try:
            network = ipaddress.ip_network(raw, strict=False)
        except ValueError:
            continue
        if ip in network:
            return True
    return False


async def _send_ack(writer: asyncio.StreamWriter, code: bytes) -> None:
    try:
        writer.write(VT + code + FS_CR)
        await writer.drain()
    except Exception:  # pragma: no cover - defensive
        logger.debug("mllp.ack.write_failed", exc_info=True)


@dataclass
class MLLPServer:
    """Inbound MLLP listener submitting jobs to the Engine queue."""

    host: str
    port: int
    allow_cidrs: list[str]
    pipeline_id: int
    store: InsightsStore
    _server: asyncio.AbstractServer | None = field(default=None, init=False)

    async def start(self) -> None:
        if self._server:
            return
        self._server = await asyncio.start_server(self._handle_client, self.host, self.port)
        logger.info(
            "mllp.listen.start",
            extra={"host": self.host, "port": self.port, "pipeline_id": self.pipeline_id},
        )

    async def stop(self) -> None:
        server = self._server
        if not server:
            return
        server.close()
        await server.wait_closed()
        self._server = None
        logger.info(
            "mllp.listen.stop",
            extra={"host": self.host, "port": self.port, "pipeline_id": self.pipeline_id},
        )

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        peer = writer.get_extra_info("peername")
        peer_ip = "unknown"
        if isinstance(peer, tuple) and peer:
            peer_ip = str(peer[0])
        logger.debug(
            "mllp.client.connect",
            extra={"host": self.host, "port": self.port, "peer": peer_ip},
        )

        if not self.allow_cidrs or not _allowed(peer_ip, self.allow_cidrs):
            logger.warning(
                "mllp.client.rejected",
                extra={"host": self.host, "port": self.port, "peer": peer_ip},
            )
            await _send_ack(writer, b"AE")
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:  # pragma: no cover - defensive
                pass
            return

        try:
            while True:
                try:
                    frame = await asyncio.wait_for(reader.readuntil(FS_CR), timeout=_READ_TIMEOUT_SECS)
                except asyncio.TimeoutError:
                    logger.warning(
                        "mllp.client.timeout",
                        extra={"host": self.host, "port": self.port, "peer": peer_ip},
                    )
                    await _send_ack(writer, b"AE")
                    break
                except asyncio.IncompleteReadError:
                    break
                if not frame:
                    break
                payload = frame[:-2]
                if payload.startswith(VT):
                    payload = payload[1:]
                if len(payload) > _MAX_FRAME_BYTES:
                    logger.warning(
                        "mllp.client.frame_too_large",
                        extra={
                            "host": self.host,
                            "port": self.port,
                            "peer": peer_ip,
                            "size": len(payload),
                        },
                    )
                    await _send_ack(writer, b"AE")
                    break
                if not payload:
                    continue

                encoded = base64.b64encode(payload).decode("ascii")
                try:
                    self.store.enqueue_job(
                        pipeline_id=self.pipeline_id,
                        kind="ingest",
                        payload={
                            "message_b64": encoded,
                            "meta": {"peer_ip": peer_ip, "transport": "mllp"},
                        },
                        priority=0,
                        max_attempts=3,
                    )
                except QueueFullError as exc:
                    logger.warning(
                        "mllp.client.backpressure",
                        extra={
                            "host": self.host,
                            "port": self.port,
                            "peer": peer_ip,
                            "error": str(exc),
                        },
                    )
                    await _send_ack(writer, b"AE")
                    break
                except Exception:
                    logger.exception(
                        "mllp.client.enqueue_failed",
                        extra={"host": self.host, "port": self.port, "peer": peer_ip},
                    )
                    await _send_ack(writer, b"AE")
                    break
                else:
                    await _send_ack(writer, b"AA")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:  # pragma: no cover - defensive
                pass
            logger.debug(
                "mllp.client.disconnect",
                extra={"host": self.host, "port": self.port, "peer": peer_ip},
            )
