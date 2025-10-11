"""Endpoint orchestration helpers."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Dict

from insights.store import InsightsStore

from .mllp_server import MLLPServer

logger = logging.getLogger(__name__)

_BIND_ANY = os.getenv("ENGINE_BIND_ANY", "0").lower() in {"1", "true", "yes"}


class EndpointManager:
    """In-process manager tracking active network endpoints."""

    def __init__(self, store: InsightsStore) -> None:
        self.store = store
        self._servers: Dict[int, MLLPServer] = {}
        self._lock = asyncio.Lock()

    async def start_endpoint(self, endpoint_id: int) -> None:
        async with self._lock:
            record = self.store.get_endpoint(endpoint_id)
            if record is None:
                raise KeyError("endpoint not found")
            if record.kind != "mllp_in":
                raise KeyError("unsupported endpoint type")
            if record.pipeline_id is None:
                raise ValueError("inbound endpoint missing pipeline_id")

            host = str(record.config.get("host") or "").strip()
            port = int(record.config.get("port") or 0)
            allow_cidrs = list(record.config.get("allow_cidrs") or [])
            if not host or port <= 0:
                raise ValueError("host and port are required")
            if host in {"0.0.0.0", "::"} and not _BIND_ANY:
                raise PermissionError("binding to wildcard host requires ENGINE_BIND_ANY=1")

            if endpoint_id in self._servers:
                logger.debug("endpoint.already_running", extra={"endpoint_id": endpoint_id})
                return

            self.store.update_endpoint(endpoint_id, status="starting", last_error=None)
            server = MLLPServer(
                host=host,
                port=port,
                allow_cidrs=allow_cidrs,
                pipeline_id=record.pipeline_id,
                store=self.store,
            )
            try:
                await server.start()
            except OSError as exc:
                logger.error(
                    "endpoint.bind_failed",
                    extra={"endpoint_id": endpoint_id, "host": host, "port": port},
                )
                self.store.update_endpoint(
                    endpoint_id, status="error", last_error=str(exc)
                )
                raise
            except Exception as exc:
                self.store.update_endpoint(
                    endpoint_id, status="error", last_error=str(exc)
                )
                raise
            else:
                self._servers[endpoint_id] = server
                self.store.update_endpoint(endpoint_id, status="running", last_error=None)

    async def stop_endpoint(self, endpoint_id: int) -> None:
        async with self._lock:
            server = self._servers.pop(endpoint_id, None)
            if server is not None:
                await server.stop()
            self.store.update_endpoint(endpoint_id, status="stopped", last_error=None)


_MANAGER: EndpointManager | None = None


def get_manager(store: InsightsStore) -> EndpointManager:
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = EndpointManager(store)
    return _MANAGER
