from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterator

__all__ = [
    "AGENT_DATA_ROOT",
    "PathViolation",
    "in_folder",
    "out_folder",
    "walk_hl7_files",
    "write_bytes",
    "synthesize_hl7",
]

AGENT_DATA_ROOT = Path(os.getenv("AGENT_DATA_ROOT", "./data/agent")).resolve()

_SAFE_RE = re.compile(r"^[\w\-.\/]+$")


class PathViolation(Exception):
    """Raised when a requested path would escape the agent data root."""


def _ensure_root() -> None:
    AGENT_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    (AGENT_DATA_ROOT / "in").mkdir(parents=True, exist_ok=True)
    (AGENT_DATA_ROOT / "out").mkdir(parents=True, exist_ok=True)


def _validate_rel(rel: str) -> None:
    if not rel or not _SAFE_RE.match(rel):
        raise PathViolation(f"unsafe path: {rel!r}")
    if ".." in Path(rel).parts:
        raise PathViolation(f"unsafe traversal: {rel!r}")


def in_folder(rel: str) -> Path:
    """Return an absolute input folder path confined to ``AGENT_DATA_ROOT/in``."""

    _ensure_root()
    _validate_rel(rel)
    path = (AGENT_DATA_ROOT / "in" / rel).resolve()
    if not str(path).startswith(str((AGENT_DATA_ROOT / "in").resolve())):
        raise PathViolation(f"outside agent input root: {rel!r}")
    path.mkdir(parents=True, exist_ok=True)
    return path


def out_folder(rel: str) -> Path:
    """Return an absolute output folder path confined to ``AGENT_DATA_ROOT/out``."""

    _ensure_root()
    _validate_rel(rel)
    path = (AGENT_DATA_ROOT / "out" / rel).resolve()
    if not str(path).startswith(str((AGENT_DATA_ROOT / "out").resolve())):
        raise PathViolation(f"outside agent output root: {rel!r}")
    path.mkdir(parents=True, exist_ok=True)
    return path


def walk_hl7_files(root: Path) -> Iterator[Path]:
    """Yield all ``*.hl7`` files under ``root`` recursively."""

    for candidate in root.rglob("*.hl7"):
        if candidate.is_file():
            yield candidate


def write_bytes(dst_dir: Path, filename: str, data: bytes) -> Path:
    """Write ``data`` into ``dst_dir / filename`` ensuring confinement."""

    dst_dir.mkdir(parents=True, exist_ok=True)
    output = (dst_dir / filename).resolve()
    if not str(output).startswith(str(dst_dir.resolve())):
        raise PathViolation("refused to escape destination directory")
    output.write_bytes(data)
    return output


def synthesize_hl7(index: int, profile: str = "ADT_A01") -> bytes:
    """Return a small demo HL7 payload for message generation."""

    msh = f"MSH|^~\\&|SILHOUETTE|CORE|DEMO|SITE|202501011200||{profile}|MSG{index:06d}|P|2.5"
    pid = f"PID|1||{100000 + index}^^^SIL^MR||Doe^{index}^John"
    return (msh + "\r" + pid + "\r").encode("utf-8")
