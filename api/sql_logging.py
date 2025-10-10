from __future__ import annotations

import json
import logging
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Tuple

from sqlalchemy import event
from sqlalchemy.engine import Engine

from api.debug_log import (
    consume_http_force_token,
    is_debug_enabled,
    last_debug_toggle_enabled,
    last_enabled_version,
    register_http_force_token,
    unregister_http_force_token,
)

__all__ = ["install_sql_logging"]

_BASE_DIR = Path(__file__).resolve().parents[1]
_DEFAULT_SQL_LOG_PATH = _BASE_DIR / "out" / "interop" / "server_sql.log"

_REDACT_KEYS = {
    "password",
    "token",
    "authorization",
    "api_key",
    "access_token",
    "refresh_token",
    "set-cookie",
    "cookie",
    "x-api-key",
    "x-auth-token",
    "x-csrf-token",
}


def _clip_text(text: str, limit: int = 2000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"…(+{len(text) - limit})"


def _clip_sql(sql: str, limit: int = 1600) -> str:
    return _clip_text(" ".join(sql.split()), limit=limit)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            if k and str(k).lower() in _REDACT_KEYS:
                out[k] = "***REDACTED***"
            else:
                out[k] = _redact(v)
        return out
    if isinstance(value, (list, tuple)):
        return [_redact(v) for v in value]
    if isinstance(value, (bytes, bytearray, memoryview)):
        return "***REDACTED***"
    if isinstance(value, str):
        return "***REDACTED***"
    return value


def _safe_params_preview(params: Any, limit: int = 800) -> str:
    try:
        red = _redact(params)
        text = json.dumps(red, ensure_ascii=False)
    except Exception:
        try:
            text = str(params)
        except Exception:
            text = "<unprintable>"
    return _clip_text(text, limit=limit)


def _ensure_logger(log_path: Path | str | None) -> Tuple[logging.Logger, bool]:
    logger = logging.getLogger("silhouette.sql")
    logger.propagate = False
    file_enabled = False

    if not any(
        isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        for h in logger.handlers
    ):
        sh = logging.StreamHandler()
        sh.setLevel(logging.INFO)
        sh.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
        logger.addHandler(sh)

    if log_path is not None:
        path = Path(log_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        if not any(
            isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", None) == str(path)
            for h in logger.handlers
        ):
            try:
                fh = RotatingFileHandler(
                    str(path),
                    maxBytes=5_000_000,
                    backupCount=3,
                    encoding="utf-8",
                )
            except OSError as exc:
                logger.warning("could not attach sql log file %s: %s", path, exc)
            else:
                fh.setLevel(logging.INFO)
                fh.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
                logger.addHandler(fh)
                file_enabled = True
        else:
            file_enabled = True

    logger.setLevel(logging.INFO)
    return logger, file_enabled


def _current_log_size(path: Path | None) -> int | None:
    if path is None:
        return None
    try:
        return path.stat().st_size
    except Exception:
        return None


def _write_fallback(path: Path | None, level: str, message: str) -> None:
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        from datetime import datetime

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
        line = f"{ts} silhouette.sql {level.upper()} {message}\n"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line)
    except Exception:
        pass


def _log_with_fallback(logger: logging.Logger, path: Path | None, level: str, msg: str) -> None:
    before = _current_log_size(path)
    try:
        getattr(logger, level)(msg)
        for h in logger.handlers:
            flush = getattr(h, "flush", None)
            if callable(flush):
                flush()
    except Exception as exc:
        print("sql log error", exc, flush=True)
    after = _current_log_size(path)
    if before is not None and after is not None and after != before:
        return
    _write_fallback(path, level, msg)


def install_sql_logging(
    engine: Engine, *, log_path: Path | str | None = _DEFAULT_SQL_LOG_PATH
) -> None:
    """Attach framed SQL logging to a SQLAlchemy Engine. Safe to call multiple times."""

    try:
        info = engine.info  # type: ignore[attr-defined]
    except AttributeError:
        info = getattr(engine, "_silhouette_sql_info", None)
        if info is None:
            info = {}
            setattr(engine, "_silhouette_sql_info", info)
    state = info.setdefault("_silhouette_sql_state", {})
    if state.get("installed"):
        return

    logger, file_enabled = _ensure_logger(log_path)
    path = Path(log_path) if log_path is not None else None

    state["logger"] = logger
    state["file_enabled"] = file_enabled
    state["log_path"] = path
    state["seen_enabled_version"] = last_enabled_version()
    state["force_token_id"] = register_http_force_token()
    state["installed"] = True

    def _should_log_now() -> bool:
        enabled_begin = is_debug_enabled()
        if enabled_begin or last_debug_toggle_enabled():
            return True
        token_id = state.get("force_token_id")
        if token_id is not None and consume_http_force_token(token_id):
            state["seen_enabled_version"] = last_enabled_version()
            return True
        ver = last_enabled_version()
        if ver > state.get("seen_enabled_version", -1):
            state["seen_enabled_version"] = ver
            return True
        return False

    @event.listens_for(engine, "before_cursor_execute")
    def _before_execute(conn, cursor, statement, parameters, context, executemany):
        context._sil_sql_should_log = _should_log_now()
        if not context._sil_sql_should_log:
            return
        context._sil_sql_t0 = time.perf_counter()
        context._sil_sql_id = f"{id(context):x}"
        op = (statement or "").lstrip().split(None, 1)
        op = op[0].upper() if op else "STATEMENT"
        dialect = conn.engine.dialect.name
        try:
            db = conn.engine.url.database or conn.engine.url.render_as_string(hide_password=True)
        except Exception:
            db = "<unknown>"
        sql_preview = _clip_sql(statement or "")
        params_preview = _safe_params_preview(parameters)
        msg = (
            f"SQL begin id={context._sil_sql_id} op={op} dialect={dialect} "
            f"db={db} sql={json.dumps(sql_preview, ensure_ascii=False)} "
            f"params={params_preview}"
        )
        _log_with_fallback(logger, path, "info", msg)

    @event.listens_for(engine, "after_cursor_execute")
    def _after_execute(conn, cursor, statement, parameters, context, executemany):
        if not getattr(context, "_sil_sql_should_log", False):
            return
        t0 = getattr(context, "_sil_sql_t0", None)
        ms = int(1000 * (time.perf_counter() - t0)) if t0 is not None else -1
        rowcount = getattr(cursor, "rowcount", -1)
        msg = f"SQL end   id={context._sil_sql_id} status=ok ms={ms} rowcount={rowcount}"
        _log_with_fallback(logger, path, "info", msg)

    @event.listens_for(engine, "handle_error")
    def _on_error(exception_context):
        context = getattr(exception_context, "execution_context", None)
        should = True
        if context is not None:
            should = getattr(context, "_sil_sql_should_log", True)
        if not should and not is_debug_enabled():
            return
        sql_preview = _clip_sql(exception_context.statement or "")
        params_preview = _safe_params_preview(exception_context.parameters)
        t0 = getattr(context, "_sil_sql_t0", None) if context is not None else None
        ms = int(1000 * (time.perf_counter() - t0)) if t0 is not None else -1
        sid = getattr(context, "_sil_sql_id", "err")
        msg = (
            f"SQL error id={sid} ms={ms} exc={type(exception_context.original_exception).__name__}: "
            f"{exception_context.original_exception} sql={json.dumps(sql_preview, ensure_ascii=False)} "
            f"params={params_preview}"
        )
        _log_with_fallback(logger, path, "info", msg)

    @event.listens_for(engine, "engine_disposed")
    def _on_disposed(eng):
        token_id = state.get("force_token_id")
        if token_id is not None:
            try:
                unregister_http_force_token(token_id)
            except Exception:
                pass
        state["installed"] = False
