from __future__ import annotations

import ast
from pathlib import Path


def suggest(path: str | Path) -> dict:
    root = Path(path)
    targets = []
    for file in root.rglob("*.py"):
        if "tests" in file.parts:
            continue
        src = file.read_text(encoding="utf-8")
        tree = ast.parse(src)
        funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")]
        if not funcs:
            continue
        test_file = root / "tests" / f"test_{file.stem}.py"
        missing = funcs if not test_file.exists() else []
        if missing:
            suggestions = [f"tests/test_{file.stem}.py::test_{f}" for f in missing]
            targets.append({"path": file.as_posix(), "missing": missing, "suggest": suggestions})
    return {
        "targets": targets,
        "heuristics": ["no direct test refs", "public API without tests"],
    }
