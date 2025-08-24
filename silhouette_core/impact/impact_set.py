from __future__ import annotations

from pathlib import Path


def compute_impact(changed_files: list[str]) -> dict:
    """Compute a minimal impact set for changed files."""
    modules = sorted(set(changed_files))
    must_run: list[str] = []
    docs: list[str] = []
    for f in changed_files:
        name = Path(f).stem
        test_path = Path("tests") / f"test_{name}.py"
        if test_path.exists():
            must_run.append(test_path.as_posix())
    readme = Path("services/api/README.md")
    if readme.exists():
        docs.append(readme.as_posix())
    return {
        "modules": modules,
        "tests": {"must_run": sorted(must_run), "suggested": []},
        "docs": {"suggested": sorted(set(docs))},
    }
