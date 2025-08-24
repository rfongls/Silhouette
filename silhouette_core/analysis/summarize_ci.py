from __future__ import annotations

from pathlib import Path


def summarize(root: Path) -> dict:
    ci_dir = root / ".github" / "workflows"
    gh_actions = any(ci_dir.glob("*.yml")) if ci_dir.is_dir() else False
    dockerfiles = [p.name for p in root.glob("Dockerfile*")]
    workflow_text = ""
    for p in ci_dir.glob("*.yml") if ci_dir.is_dir() else []:
        workflow_text += p.read_text(encoding="utf-8") + "\n"
    py_lint = ["ruff"] if "ruff" in workflow_text else []
    py_test = ["pytest"] if "pytest" in workflow_text else []
    py_type = ["mypy"] if "mypy" in workflow_text else []
    node_test = ["npm test"] if "npm test" in workflow_text else []
    notes = []
    if "bandit" in workflow_text:
        notes.append("bandit configured")
    if "hadolint" in workflow_text:
        notes.append("hadolint present")
    return {
        "ci_tools": {"gh_actions": gh_actions, "dockerfiles": dockerfiles},
        "python": {"lint": py_lint, "test": py_test, "type_check": py_type},
        "node": {"test": node_test},
        "notes": notes,
    }
