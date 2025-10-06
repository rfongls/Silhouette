from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Iterable, List, Tuple

_BASE_DIR = Path(__file__).resolve().parents[1]
LOG_DIR = _BASE_DIR / "out" / "interop"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "generator_debug.log"
_MAX_BUFFER = 2000

_buffer: deque[str] = deque(maxlen=_MAX_BUFFER)
_lock = Lock()
_enabled: bool = False


def is_debug_enabled() -> bool:
    with _lock:
        return _enabled


def set_debug_enabled(enabled: bool) -> bool:
    global _enabled
    enabled = bool(enabled)
    with _lock:
        changed = _enabled != enabled
        _enabled = enabled
    if changed:
        state = "on" if enabled else "off"
        log_debug_message(f"debug.enabled state={state}", force=True)
    return enabled


def toggle_debug_enabled() -> bool:
    return set_debug_enabled(not is_debug_enabled())


def _timestamp() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def log_debug_message(text: str, *, force: bool = False) -> bool:
    if not force and not is_debug_enabled():
        return False
    record_debug_line(text)
    return True


def _format_value(value: Any, limit: int = 160) -> str:
    if value is None:
        return "None"
    try:
        if isinstance(value, (bytes, bytearray)):
            text = value.decode("utf-8", errors="replace")
        else:
            text = str(value)
    except Exception:
        text = repr(value)
    text = text.replace("\r", "\\r").replace("\n", "\\n")
    if len(text) > limit:
        extra = len(text) - limit
        text = f"{text[:limit]}…(+{extra})"
    return text


def _format_event(event: str, fields: Tuple[Tuple[str, Any], ...]) -> str:
    parts = [event]
    for key, value in fields:
        parts.append(f"{key}={_format_value(value)}")
    return " | ".join(parts)


def log_debug_event(event: str, **fields: Any) -> bool:
    message = _format_event(event, tuple(fields.items()))
    return log_debug_message(message)


def record_debug_line(text: str) -> str:
    """Append a debug line to the rolling buffer and backing file."""
    if not isinstance(text, str):
        text = str(text)
    line = f"{_timestamp()} {text}".rstrip()
    path = LOG_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        _buffer.append(line)
        try:
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except Exception:
            # If the file cannot be written, we still keep the in-memory buffer.
            pass
    return line


def tail_debug_lines(limit: int = 200) -> List[str]:
    """Return up to ``limit`` of the most recent debug lines."""
    if limit is None or limit <= 0:
        limit = len(_buffer)
    with _lock:
        if limit >= len(_buffer):
            return list(_buffer)
        return list(_buffer)[-limit:]


def iter_debug_file() -> Iterable[str]:
    """Yield all lines from the persisted debug log file (if it exists)."""
    path = LOG_FILE
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                yield line.rstrip("\n")
    except FileNotFoundError:
        return


def reset_debug_log(clear_file: bool = False) -> None:
    """Utility for tests: clear the in-memory buffer (and file when requested)."""
    path = LOG_FILE
    with _lock:
        _buffer.clear()
    if clear_file:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


__all__ = [
    "LOG_FILE",
    "is_debug_enabled",
    "set_debug_enabled",
    "toggle_debug_enabled",
    "log_debug_event",
    "log_debug_message",
    "record_debug_line",
    "tail_debug_lines",
    "iter_debug_file",
    "reset_debug_log",
]
