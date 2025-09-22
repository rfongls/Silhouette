"""Shared HTTP request/response logging middleware configuration."""
from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from starlette.responses import Response as StarletteResponse

from api.debug_log import is_debug_enabled

__all__ = ["install_http_logging"]

_BASE_DIR = Path(__file__).resolve().parents[1]
_DEFAULT_HTTP_LOG_PATH = _BASE_DIR / "out" / "interop" / "server_http.log"

_TEXTUAL_CONTENT_PREFIXES = (
    "text/",
    "application/json",
    "application/xml",
    "application/javascript",
    "application/problem+json",
)

_REDACT_KEYS = {
    "password",
    "token",
    "authorization",
    "api_key",
    "access_token",
    "refresh_token",
}


def _clip_bytes(data: bytes, limit: int = 2000) -> str:
    if not data:
        return ""
    text = data.decode("utf-8", errors="replace")
    if len(text) <= limit:
        return text
    return text[:limit] + f"…(+{len(text) - limit})"


def _redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, inner in value.items():
            if key and key.lower() in _REDACT_KEYS:
                redacted[key] = "***REDACTED***"
            else:
                redacted[key] = _redact_secrets(inner)
        return redacted
    if isinstance(value, list):
        return [_redact_secrets(v) for v in value]
    return value


def _safe_json_preview(data: bytes) -> str:
    if not data:
        return ""
    try:
        parsed = json.loads(data.decode("utf-8"))
    except Exception:
        return _clip_bytes(data)
    parsed = _redact_secrets(parsed)
    try:
        return json.dumps(parsed)[:2000]
    except Exception:
        return _clip_bytes(data)


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


def _ensure_logger(log_path: Path | str | None) -> logging.Logger:
    logger = logging.getLogger("silhouette.http")

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

    logger.setLevel(logging.INFO)
    return logger


def _log_safe(
    logger: logging.Logger, level: str, message: str, *args: Any, **kwargs: Any
) -> None:
    try:
        getattr(logger, level)(message, *args, **kwargs)
    except Exception:
        # Logging must never interrupt the request lifecycle.
        pass


def install_http_logging(
    app: FastAPI,
    *,
    log_path: Path | str | None = _DEFAULT_HTTP_LOG_PATH,
) -> None:
    """Attach the shared HTTP logging middleware to *app*.

    The middleware captures the request payload, logs a safe preview, and
    replays the body for downstream handlers. Responses are buffered only for
    textual payloads so static/binary assets are not copied into memory.
    """

    if getattr(app.state, "_silhouette_http_logging_installed", False):
        return

    http_logger = _ensure_logger(log_path)
    _log_safe(http_logger, "info", "HTTP logging middleware installed; log_path=%s", str(log_path))

    async def http_action_logger(request: Request, call_next):
        if not is_debug_enabled():
            return await call_next(request)
        start = time.time()
        raw_body = await request.body()

        async def receive() -> dict[str, Any]:
            return {"type": "http.request", "body": raw_body, "more_body": False}

        replayable_request = Request(request.scope, receive)
        action = f"{request.method} {request.url.path}"
        vars_preview = {
            "query": dict(request.query_params),
            "ctype": request.headers.get("content-type"),
            "raw_len": len(raw_body or b""),
            "body_preview": _safe_json_preview(raw_body),
        }
        _log_safe(http_logger, "info", "Action=%s Vars=%s", action, vars_preview)

        try:
            response = await call_next(replayable_request)
        except Exception:
            elapsed_ms = int(1000 * (time.time() - start))
            _log_safe(http_logger, "exception", "Action=%s Response=<exception> ms=%s", action, elapsed_ms)
            raise

        content_type = ""
        if hasattr(response, "headers") and response.headers is not None:
            content_type = response.headers.get("content-type") or ""
        skip_reason = _should_skip_logging(request.url.path, content_type)
        if skip_reason:
            elapsed_ms = int(1000 * (time.time() - start))
            _log_safe(
                http_logger,
                "info",
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
        _log_safe(
            http_logger,
            "info",
            "Action=%s Response={status:%s, ms:%s, preview:%s}",
            action,
            response.status_code,
            elapsed_ms,
            _clip_bytes(body),
        )
        return new_response

    app.middleware("http")(http_action_logger)
    app.state._silhouette_http_logging_installed = True
