from __future__ import annotations

import os
from pathlib import Path
from ..repo_map import _owners_for as _repo_owners_for, _read_codeowners


def _owners_for(service: Path, root: Path) -> list[str]:
    rules = _read_codeowners(root)
    if not rules:
        return []
    return _repo_owners_for(service.as_posix().rstrip("/"), rules)


def _has_test(path: str, root: Path) -> bool:
    test_path = root / "tests" / f"test_{Path(path).stem}.py"
    return test_path.exists()


def analyze(service_path: str | Path, graph: dict[str, set[str]], root: Path) -> dict:
    service = Path(service_path)
    service_str = service.as_posix().rstrip("/") + "/"
    files = [p for p in graph if p.startswith(service_str)]
    languages = sorted({Path(f).suffix.lstrip('.') for f in files})
    inbound = sorted({src for src, dsts in graph.items() for dst in dsts if dst in files})
    outbound = sorted({dst for f in files for dst in graph.get(f, set()) if dst not in files})
    owners = _owners_for(service, root)
    risks = {
        "no_tests": [f for f in files if not _has_test(f, root)],
        "high_centrality": [],
    }
    entrypoints = [f for f in files if os.path.basename(f) in {"main.py", "index.ts"}]
    summary = {"files": len(files), "languages": languages}
    deps = {"inbound": inbound, "outbound": outbound}
    return {
        "service": service.as_posix(),
        "summary": summary,
        "deps": deps,
        "owners": owners,
        "risks": risks,
        "entrypoints": entrypoints,
    }
