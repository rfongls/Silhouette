from __future__ import annotations
import subprocess
from pathlib import Path
from typing import Callable

def run_stream(cmd: list[str], cwd: Path, on_line: Callable[[str], None]) -> int:
    """Run a command and stream stdout/stderr line by line."""
    proc = subprocess.Popen(cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert proc.stdout is not None
    for line in iter(proc.stdout.readline, ""):
        on_line(line.rstrip("\n"))
    proc.stdout.close()
    return proc.wait()

def run_quiet(cmd: list[str], cwd: Path) -> int:
    return subprocess.call(cmd, cwd=str(cwd))
