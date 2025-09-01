from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
import subprocess
import time


@dataclass
class Deny(Exception):
    reason: str

    def __str__(self) -> str:  # pragma: no cover - simple data container
        return self.reason


def _load_scope(scope_file: str | Path) -> list[str]:
    """Load scope lines; ignore blanks/comments. Offline and permissive for scaffold."""
    p = Path(scope_file)
    if not p.exists():
        return []
    lines: list[str] = []
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(s)
    return lines


def _in_scope(target: str, scope_lines: list[str]) -> bool:
    """Very simple matcher:
    - exact match
    - suffix domain match: lines starting with '*.' will match subdomains
    - CIDR/IP support can be added later; for now just exact match for IP strings
    """
    target = (target or "").strip().lower()
    if not target or not scope_lines:
        return False
    for s in scope_lines:
        s_l = s.lower()
        if s_l == target:
            return True
        if s_l.startswith("*.") and target.endswith(s_l[1:]):
            return True
    return False


def require_auth_and_scope(scope_file: str | Path, target: str) -> None:
    """Scaffolded gate: ensure target is in provided scope file."""
    scope = _load_scope(scope_file)
    if not scope:
        raise Deny(f"Scope not found or empty: {scope_file}")
    if not _in_scope(target, scope):
        raise Deny(f"Target '{target}' not in scope file: {scope_file}")


def run_docker(image: str, cmd: str, mounts: list[str] | None = None,
               network_host: bool = False, timeout: int = 600):
    """Minimal helper to run a docker image with optional mounts."""
    mounts = mounts or []
    base = ["docker", "run", "--rm"]
    if network_host:
        base += ["--network", "host"]
    for m in mounts:
        base += ["-v", m]
    full = base + [image, "bash", "-lc", cmd]
    res = subprocess.run(full, capture_output=True, text=True, timeout=timeout)
    return res.returncode, res.stdout, res.stderr


def _run_dir(out_root: str = "out/security") -> Path:
    root = Path(out_root)
    root.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    run = root / ts
    run.mkdir(parents=True, exist_ok=True)
    return run


def write_result(name: str, data: dict, out_root: str = "out/security") -> str:
    """Write a JSON result for a skill into out/security/<ts>/active/<name>.json"""
    run = _run_dir(out_root)
    active = run / "active"
    active.mkdir(parents=True, exist_ok=True)
    path = active / f"{name}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return str(path)

