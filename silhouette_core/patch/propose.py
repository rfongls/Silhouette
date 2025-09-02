from __future__ import annotations

import difflib
import fnmatch
import io
from pathlib import Path

import yaml


def _load_policy() -> dict:
    for p in [Path("policy.yaml"), Path(__file__).resolve().parents[2] / "policy.yaml"]:
        try:
            with open(p, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            continue
    return {}


def _is_protected(path: str, patterns: list[str]) -> bool:
    posix = Path(path).as_posix()
    return any(
        fnmatch.fnmatch(posix, pat)
        or (pat.endswith("/**") and posix.startswith(pat[:-3]))
        or pat in posix
        for pat in patterns
    )


def propose_patch(goal: str, hints: list[str] | None = None, strategy: str = "textual") -> dict:
    """Propose a patch without modifying files on disk."""
    hints = sorted(hints or [])
    policy = _load_policy()
    protected = policy.get("protected_paths", [])
    diff_io = io.StringIO()
    files_changed: list[str] = []
    insertions = deletions = 0
    notes: list[str] = []
    allowed_ops = policy.get("allowed_ops", {})
    if not allowed_ops.get("propose_patch", True):
        notes.append("policy disallows propose_patch; treating as dry-run")

    for hint in hints:
        if _is_protected(hint, protected):
            notes.append(f"skipped protected path: {hint}")
            continue
        try:
            original_text = Path(hint).read_text(encoding="utf-8").replace("\r\n", "\n")
            original = original_text.splitlines(keepends=True)
        except FileNotFoundError:
            notes.append(f"missing file: {hint}")
            continue
        new_lines = [f"# TODO: {goal}\n"] + original
        diff_lines = list(
            difflib.unified_diff(original, new_lines, fromfile=hint, tofile=hint, lineterm="")
        )
        if diff_lines:
            diff_io.write("\n".join(diff_lines) + "\n")
            files_changed.append(hint)
            insertions += 1
    summary = {
        "files_changed": sorted(files_changed),
        "insertions": insertions,
        "deletions": deletions,
    }
    return {"diff": diff_io.getvalue(), "summary": summary, "notes": notes}
