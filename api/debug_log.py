from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Iterable, List

LOG_FILE = Path("out/interop/generator_debug.log")
_MAX_BUFFER = 2000

_buffer: deque[str] = deque(maxlen=_MAX_BUFFER)
_lock = Lock()


def _timestamp() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


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
    "record_debug_line",
    "tail_debug_lines",
    "iter_debug_file",
    "reset_debug_log",
]
