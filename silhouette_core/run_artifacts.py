from __future__ import annotations

import json
import platform
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


def _git_commit(repo_root: Path) -> str | None:
    try:
        return (
            subprocess.check_output(
                ["git", "-C", str(repo_root), "rev-parse", "HEAD"], text=True
            ).strip()
        )
    except Exception:
        return None


@contextmanager
def record_run(
    command: str,
    args: dict[str, object],
    repo_root: Path,
    policy_path: Path | None = None,
) -> Iterator[Path]:
    start = datetime.utcnow()
    ts = start.strftime("%Y%m%d_%H%M%S")
    run_dir = Path("artifacts") / ts
    run_dir.mkdir(parents=True, exist_ok=True)
    try:
        yield run_dir
    finally:
        finished = datetime.utcnow()
        data = {
            "command": command,
            "args": args,
            "repo_root": str(repo_root),
            "git_commit": _git_commit(repo_root),
            "policy_path": str(policy_path) if policy_path else None,
            "environment": {
                "python": platform.python_version(),
                "platform": platform.platform(),
            },
            "started": start.isoformat() + "Z",
            "finished": finished.isoformat() + "Z",
        }
        (run_dir / "silhouette_run.json").write_text(json.dumps(data, indent=2))
