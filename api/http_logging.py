"""Shared HTTP request/response logging middleware configuration."""
from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Tuple

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
from starlette.requests import ClientDisconnect

from api.debug_log import (
    consume_http_force_token,
    is_debug_enabled,
    last_debug_toggle_enabled,
    last_enabled_version,
    register_http_force_token,
    unregister_http_force_token,
)
from api.redaction import redact

__all__ = ["HttpLoggerMiddleware", "install_http_logging"]

_BASE_DIR = Path(__file__).resolve().parents[1]
_DEFAULT_HTTP_LOG_PATH = _BASE_DIR / "out" / "interop" / "server_http.log"

_TEXTUAL_CONTENT_PREFIXES = (
    "text/",
    "application/json",
    "application/xml",
    "application/javascript",
    "application/problem+json",
)

def _safe_json_preview(data: bytes | None, limit: int = 2000) -> str:
    """Return a short JSON preview with secret keys redacted."""

    if not data:
        return ""
    try:
        obj = json.loads(data.decode("utf-8", errors="replace"))
    except Exception:
        return _clip_bytes(data, limit=limit)
    try:
        redacted = _redact_secrets(obj)
    except Exception:
        redacted = obj
    try:
        text = json.dumps(redacted, ensure_ascii=False)
    except Exception:
        return _clip_bytes(data, limit=limit)
    if len(text) <= limit:
        return text
    return text[:limit] + f"…(+{len(text) - limit})"


def _clip_bytes(data: bytes, limit: int = 2000) -> str:
    if not data:
        return ""
    text = data.decode("utf-8", errors="replace")
    if len(text) <= limit:
        return text
    return text[:limit] + f"…(+{len(text) - limit})"


def _redact_secrets(value: Any) -> Any:
    return redact(value)


def _should_skip_logging(path: str, content_type: str | None) -> str | None:
    if path.startswith("/static"):
        return "static"
    lowered = (content_type or "").lower()
    if not lowered:
        return None
    for prefix in _TEXTUAL_CONTENT_PREFIXES:
        if lowered.startswith(prefix):
            return None
    return "binary"


def _ensure_logger(log_path: Path | str | None) -> Tuple[logging.Logger, bool]:
    logger = logging.getLogger("silhouette.http")
    logger.propagate = False
    file_logging_enabled = False

    if not any(
        isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler)
        for handler in logger.handlers
    ):
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(
            logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
        )
        logger.addHandler(stream_handler)

    if log_path is not None:
        path = Path(log_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.warning("could not create http log directory %s: %s", path.parent, exc)
        else:
            existing = next(
                (handler for handler in logger.handlers if getattr(handler, "baseFilename", None) == str(path)),
                None,
            )
            if existing is None:
                try:
                    file_handler = RotatingFileHandler(
                        path,
                        maxBytes=5_000_000,
                        backupCount=3,
                        encoding="utf-8",
                    )
                except OSError as exc:
                    logger.warning("could not attach http log file %s: %s", path, exc)
                else:
                    file_handler.setLevel(logging.INFO)
                    file_handler.setFormatter(
                        logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
                    )
                    logger.addHandler(file_handler)
                    file_logging_enabled = True
            else:
                file_logging_enabled = True

    logger.setLevel(logging.INFO)
    return logger, file_logging_enabled


def _log_safe(
    logger: logging.Logger, level: str, message: str, *args: Any, **kwargs: Any
) -> None:
    try:
        getattr(logger, level)(message, *args, **kwargs)
        for handler in logger.handlers:
            flush = getattr(handler, "flush", None)
            if callable(flush):
                flush()
    except Exception as exc:
        print("log error", exc, flush=True)
        # Logging must never interrupt the request lifecycle.
        pass


class HttpLoggerMiddleware(BaseHTTPMiddleware):
    """Best-effort request logger that cannot break the request pipeline.

    Impact analysis:
    - Pros: auto-creates the HTTP log directory on startup and falls back to
      console logging if file I/O fails, preventing first-hit 500 errors on new
      machines.
    - Cons: when file logging is unavailable only the console stream is
      populated, reducing historical retention.
    """

    def __init__(
        self,
        app,
        *,
        log_path: Path | str | None = _DEFAULT_HTTP_LOG_PATH,
    ) -> None:
        super().__init__(app)
        self._raw_log_path = Path(log_path) if log_path is not None else None
        self.logger, self.file_logging_enabled = _ensure_logger(self._raw_log_path)
        self._seen_enabled_version = last_enabled_version()
        self._http_token_id = register_http_force_token()
        if hasattr(app, "add_event_handler"):
            try:
                app.add_event_handler("shutdown", self._unregister_token)
            except Exception:
                pass
        display_path = str(self._raw_log_path) if self._raw_log_path is not None else "<disabled>"
        self._log_with_fallback("info", "HTTP logging middleware installed; log_path=%s", display_path)

    def _write_fallback_log(self, level: str, message: str, *args: Any) -> None:
        if self._raw_log_path is None:
            return
        try:
            path = self._raw_log_path
            formatted = message % args if args else message
        except Exception:
            formatted = message
        try:
            path = self._raw_log_path
            path.parent.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
            line = f"{timestamp} silhouette.http {level.upper()} {formatted}\n"
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line)
        except Exception:
            pass

    def _current_log_size(self) -> int | None:
        if self._raw_log_path is None:
            return None
        try:
            return self._raw_log_path.stat().st_size
        except Exception:
            return None

    def _log_with_fallback(self, level: str, message: str, *args: Any) -> None:
        before = self._current_log_size()
        _log_safe(self.logger, level, message, *args)
        if self.file_logging_enabled:
            after = self._current_log_size()
            if before is not None and after is not None and after != before:
                return
        self._write_fallback_log(level, message, *args)

    def _unregister_token(self) -> None:
        token_id = getattr(self, "_http_token_id", None)
        if token_id is None:
            return
        unregister_http_force_token(token_id)
        self._http_token_id = None

    def __del__(self) -> None:
        try:
            self._unregister_token()
        except Exception:
            pass

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        start = time.time()
        action = f"{request.method} {request.url.path}"
        enabled_at_start = is_debug_enabled()
        toggle_state = last_debug_toggle_enabled()
        log_request = enabled_at_start or toggle_state
        enabled_version = last_enabled_version()
        token_id = getattr(self, "_http_token_id", None)
        if token_id is not None and consume_http_force_token(token_id):
            log_request = True
            self._seen_enabled_version = last_enabled_version()
        if enabled_version > self._seen_enabled_version:
            log_request = True
            self._seen_enabled_version = enabled_version

        raw_body: bytes | None = None
        replayable_request: Request = request
        if log_request:
            try:
                raw_body = await request.body()
            except ClientDisconnect:
                raw_body = b""

            async def receive() -> dict[str, Any]:
                return {"type": "http.request", "body": raw_body or b"", "more_body": False}

            replayable_request = Request(request.scope, receive)

        vars_preview = {
            "query": _redact_secrets(dict(request.query_params)),
            "ctype": request.headers.get("content-type"),
            "raw_len": len(raw_body) if raw_body is not None else None,
            "body_preview": _safe_json_preview(raw_body) if raw_body is not None else "<not captured>",
        }
        if log_request:
            self._log_with_fallback("info", "Action=%s Vars=%s", action, vars_preview)

        try:
            response = await call_next(replayable_request)
        except Exception:
            if enabled_at_start or is_debug_enabled():
                elapsed_ms = int(1000 * (time.time() - start))
                self._log_with_fallback(
                    "exception",
                    "Action=%s Response=<exception> ms=%s",
                    action,
                    elapsed_ms,
                )
            raise

        enabled_after = is_debug_enabled()
        if not log_request and not enabled_after:
            return response

        if not log_request and enabled_after:
            log_request = True
            self._log_with_fallback("info", "Action=%s Vars=%s", action, vars_preview)
            self._seen_enabled_version = last_enabled_version()

        content_type = ""
        if hasattr(response, "headers") and response.headers is not None:
            content_type = response.headers.get("content-type") or ""
        skip_reason = _should_skip_logging(request.url.path, content_type)
        if skip_reason:
            elapsed_ms = int(1000 * (time.time() - start))
            self._log_with_fallback(
                "info",
                "Action=%s Response={status:%s, ms:%s, preview:<skipped %s>}",
                action,
                response.status_code,
                elapsed_ms,
                skip_reason,
            )
            self._write_fallback_log(
                "Action=%s Response={status:%s, ms:%s, preview:<skipped %s>}",
                action,
                response.status_code,
                elapsed_ms,
                skip_reason,
            )
            return response

        body = b""
        if hasattr(response, "body_iterator") and response.body_iterator is not None:
            async for chunk in response.body_iterator:
                body += chunk
        elif hasattr(response, "body"):
            if isinstance(response.body, (bytes, bytearray)):
                body = bytes(response.body)
            elif isinstance(response.body, str):
                body = response.body.encode("utf-8", errors="replace")

        headers = dict(response.headers) if hasattr(response, "headers") else {}
        headers.pop("content-length", None)
        new_response = StarletteResponse(
            content=body,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type,
            background=response.background,
        )
        elapsed_ms = int(1000 * (time.time() - start))
        self._log_with_fallback(
            "info",
            "Action=%s Response={status:%s, ms:%s, preview:%s}",
            action,
            response.status_code,
            elapsed_ms,
            _clip_bytes(body),
        )
        self._write_fallback_log(
            "Action=%s Response={status:%s, ms:%s, preview:%s}",
            action,
            response.status_code,
            elapsed_ms,
            _clip_bytes(body),
        )
        return new_response


def install_http_logging(
    app: FastAPI,
    *,
    log_path: Path | str | None = _DEFAULT_HTTP_LOG_PATH,
) -> None:
    """Attach the shared HTTP logging middleware to *app*."""

    if getattr(app.state, "_silhouette_http_logging_installed", False):
        return

    app.add_middleware(HttpLoggerMiddleware, log_path=log_path)
    app.state._silhouette_http_logging_installed = True
