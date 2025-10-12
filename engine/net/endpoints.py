"""Endpoint orchestration helpers."""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import time
from pathlib import Path
from datetime import datetime
from typing import Dict

from agent.fs_utils import out_folder, write_bytes
from engine.operators.transform import TransformOperator
from engine.runtime import EngineRuntime
from insights.store import InsightsStore

from .mllp_server import MLLPServer

logger = logging.getLogger(__name__)

_BIND_ANY = os.getenv("ENGINE_NET_BIND_ANY", "0").lower() in {"1", "true", "yes"}


class EndpointManager:
    """In-process manager tracking active network endpoints."""

    def __init__(self, store: InsightsStore) -> None:
        self.store = store
        self._servers: Dict[int, MLLPServer] = {}
        self._runtime_cache: Dict[int, EngineRuntime | None] = {}
        self._lock = asyncio.Lock()

    def _next_daily_seq(self, directory: Path) -> tuple[str, int]:
        """Return the next YYYYMMDD sequence tuple for the provided directory."""

        today = datetime.utcnow().strftime("%Y%m%d")
        seq_file = directory / f".seq_{today}"
        lock_file = directory / f".seq_{today}.lock"

        fd: int | None = None
        for _ in range(20):
            try:
                fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                break
            except FileExistsError:
                time.sleep(0.05)
        else:
            fd = None

        try:
            current = 0
            if seq_file.exists():
                try:
                    current = int(seq_file.read_text(encoding="utf-8").strip() or "0")
                except Exception:
                    current = 0
            next_seq = current + 1
            try:
                seq_file.write_text(str(next_seq), encoding="utf-8")
            except Exception:
                pass
            return today, next_seq
        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
                try:
                    os.remove(lock_file)
                except OSError:
                    pass

    async def start_endpoint(self, endpoint_id: int) -> None:
        async with self._lock:
            record = self.store.get_endpoint(endpoint_id)
            if record is None:
                raise KeyError("endpoint not found")
            if record.kind != "mllp_in":
                raise KeyError("unsupported endpoint type")

            host = str(record.config.get("host") or "").strip()
            port = int(record.config.get("port") or 0)
            allow_cidrs = list(record.config.get("allow_cidrs") or [])
            if not host or port <= 0:
                raise ValueError("host and port are required")
            if host in {"0.0.0.0", "::"} and not _BIND_ANY:
                raise PermissionError("binding to wildcard host requires ENGINE_NET_BIND_ANY=1")

            if endpoint_id in self._servers:
                logger.debug("endpoint.already_running", extra={"endpoint_id": endpoint_id})
                return

            self.store.update_endpoint(endpoint_id, status="starting", last_error=None)

            if record.pipeline_id is not None:
                self._runtime_cache.pop(record.pipeline_id, None)

            async def _handler(payload: bytes, meta: dict[str, str]) -> None:
                await self._process_incoming(endpoint_id, payload, meta)

            server = MLLPServer(
                host=host,
                port=port,
                allow_cidrs=allow_cidrs,
                pipeline_id=record.pipeline_id,
                store=self.store,
                message_handler=_handler,
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

    async def reprocess_incoming(
        self,
        endpoint_id: int,
        payload: bytes,
        meta: dict[str, str] | None = None,
    ) -> None:
        """Public hook used by APIs to replay failed messages."""

        await self._process_incoming(endpoint_id, payload, dict(meta or {}))

    async def _process_incoming(self, endpoint_id: int, payload: bytes, meta: dict[str, str]) -> None:
        meta = dict(meta or {})
        record = self.store.get_endpoint(endpoint_id)
        if record is None:
            raise RuntimeError("endpoint not found")
        runtime: EngineRuntime | None = None
        if record.pipeline_id is not None:
            runtime = self._resolve_runtime(record.pipeline_id)

        if runtime is None and record.pipeline_id is not None:
            encoded = base64.b64encode(payload).decode("ascii")
            self.store.enqueue_job(
                pipeline_id=record.pipeline_id,
                kind="ingest",
                payload={"message_b64": encoded, "meta": meta},
                priority=0,
                max_attempts=3,
            )
            return

        processed = payload
        try:
            if runtime is not None:
                processed = await runtime.run_on_message(payload)

            self._persist_message(
                endpoint_id=record.id,
                sink_kind=record.sink_kind,
                sink_config=record.sink_config,
                raw=payload,
                processed=processed,
                meta=meta,
            )
        except Exception as exc:  # noqa: BLE001 - capture and store failure context
            logger.exception(
                "endpoint.pipeline.failure",
                extra={
                    "endpoint_id": record.id,
                    "pipeline_id": record.pipeline_id,
                },
            )
            self.store.save_failed_message(
                endpoint_id=record.id,
                pipeline_id=record.pipeline_id,
                raw=payload,
                error=str(exc),
                meta=meta,
            )
            return

    def _persist_message(
        self,
        *,
        endpoint_id: int,
        sink_kind: str,
        sink_config: dict[str, object] | None,
        raw: bytes,
        processed: bytes,
        meta: dict[str, str],
    ) -> None:
        if sink_kind == "db":
            self.store.save_endpoint_message(
                endpoint_id=endpoint_id,
                raw=raw,
                processed=processed,
                meta=dict(meta),
            )
            return

        folder = ""
        if sink_config and isinstance(sink_config, dict):
            folder = str(sink_config.get("folder") or "")
        if not folder:
            folder = f"endpoint_{endpoint_id}"
        directory = Path(out_folder(folder))
        date_str, seq = self._next_daily_seq(directory)
        filename = f"{date_str}_{seq}.hl7"
        write_bytes(directory, filename, processed)

    def _resolve_runtime(self, pipeline_id: int) -> EngineRuntime | None:
        if pipeline_id in self._runtime_cache:
            return self._runtime_cache[pipeline_id]

        steps = self.store.list_pipeline_steps(pipeline_id)
        if not steps:
            self._runtime_cache[pipeline_id] = None
            return None

        operators = []
        for step in steps:
            profile = step.profile
            if profile.kind == "transform":
                operators.append(TransformOperator(profile.config))
            else:
                logger.warning(
                    "endpoint.pipeline.unsupported_step",
                    extra={
                        "pipeline_id": pipeline_id,
                        "step_id": step.id,
                        "profile_kind": profile.kind,
                    },
                )
        if not operators:
            self._runtime_cache[pipeline_id] = None
            return None

        runtime = EngineRuntime(spec=None, operators=operators)
        self._runtime_cache[pipeline_id] = runtime
        return runtime


_MANAGER: EndpointManager | None = None


def get_manager(store: InsightsStore) -> EndpointManager:
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = EndpointManager(store)
    return _MANAGER
