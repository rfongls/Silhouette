"""Minimal always-on activity logging for user-facing actions."""
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, List

_BASE_DIR = Path(__file__).resolve().parents[1]
LOG_DIR = _BASE_DIR / "out" / "interop"
LOG_DIR.mkdir(parents=True, exist_ok=True)
ACTIVITY_FILE = LOG_DIR / "activity.log"

_buffer: deque[str] = deque(maxlen=400)
_lock = Lock()


def _timestamp() -> str:
    now = datetime.now(timezone.utc)
    return now.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _format_fields(**fields: Any) -> str:
    parts: list[str] = []
    for key, value in fields.items():
        try:
            rendered = str(value)
        except Exception:
            rendered = repr(value)
        rendered = rendered.replace("\r", "\\r").replace("\n", "\\n")
        parts.append(f"{key}={rendered}")
    return " | ".join(parts)


def log_activity(event: str, **fields: Any) -> None:
    """Record a lightweight audit event to memory and disk."""

    line = f"{_timestamp()} activity | event={event}"
    extras = _format_fields(**fields)
    if extras:
        line = f"{line} | {extras}"
    with _lock:
        _buffer.append(line)
        try:
            with ACTIVITY_FILE.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except Exception:
            # Do not let logging failures disrupt the main flow.
            pass


def tail_activity_lines(limit: int = 100) -> List[str]:
    with _lock:
        if limit <= len(_buffer):
            return list(_buffer)[-limit:]
    try:
        with ACTIVITY_FILE.open("r", encoding="utf-8", errors="replace") as handle:
            lines = handle.readlines()
    except FileNotFoundError:
        return []
    except Exception:
        return []
    return [line.rstrip("\n") for line in lines[-limit:]]


__all__ = ["ACTIVITY_FILE", "log_activity", "tail_activity_lines"]
