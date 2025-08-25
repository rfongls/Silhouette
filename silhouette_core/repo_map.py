from __future__ import annotations

import fnmatch
import hashlib
import json
import os
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

from .analysis import summarize_ci as analysis_summarize_ci
from .graph.dep_graph import build_dep_graph

LANG_MAP = {
    ".py": "py",
    ".ts": "ts",
    ".tsx": "ts",
    ".js": "js",
    ".jsx": "js",
    ".go": "go",
    ".java": "java",
    ".cs": "cs",
}


def _lang_for_path(path: Path) -> str | None:
    return LANG_MAP.get(path.suffix.lower())


def _centrality(graph: dict[str, set[str]]) -> dict[str, float]:
    indeg = defaultdict(int)
    for _src, dsts in graph.items():
        for dst in dsts:
            indeg[dst] += 1
    centrality: dict[str, float] = {}
    max_deg = 1
    for node, dsts in graph.items():
        deg = len(dsts) + indeg.get(node, 0)
        centrality[node] = deg
        if deg > max_deg:
            max_deg = deg
    for node in centrality:
        centrality[node] /= max_deg
    return centrality


def _read_codeowners(root: Path) -> list[tuple[str, list[str]]]:
    """Return list of (pattern, [owners]) rules from CODEOWNERS; first file found wins."""
    for loc in (root / ".github" / "CODEOWNERS", root / "CODEOWNERS"):
        if loc.is_file():
            rules: list[tuple[str, list[str]]] = []
            for line in loc.read_text(encoding="utf-8", errors="ignore").splitlines():
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                parts = s.split()
                if len(parts) >= 2:
                    pattern = parts[0]
                    owners = [p for p in parts[1:] if p.startswith("@")]
                    rules.append((pattern, owners))
            return rules
    return []


def _owners_for(path_rel: str, rules: list[tuple[str, list[str]]]) -> list[str]:
    """Resolve owners for a repo-relative path using GitHub-like matching (last match wins).
    Handles patterns that may begin with '/'."""
    p = path_rel.replace("\\", "/")
    owners: list[str] = []
    for pattern, o in rules:
        patt = pattern.lstrip("/")
        if fnmatch.fnmatch(p, patt) or fnmatch.fnmatch(p + "/", patt):
            owners = o
    return owners


def _service_candidates(root: Path, code_files: list[str]) -> list[str]:
    services: set[str] = set()
    for rel in code_files:
        parts = Path(rel).parts
        if parts and parts[0] in {"services", "src"} and len(parts) >= 2:
            services.add("/".join(parts[:2]))
        elif len(parts) >= 2:
            services.add(parts[0])
    return sorted(services)


def build_repo_map(root: Path, files: Iterable[str], compute_hashes: bool = False) -> dict:
    root = root.resolve()
    detected = []
    language_counts: dict[str, int] = {}
    file_entries: list[dict[str, object]] = []
    code_paths: list[str] = []
    code_file_count = 0
    for rel in files:
        rel_path = Path(rel)
        p = root / rel_path
        if not p.is_file():
            continue
        size = p.stat().st_size
        rel_norm = rel_path.as_posix()
        entry: dict[str, object] = {"path": rel_norm, "size": size}
        lang = _lang_for_path(p)
        if lang:
            detected.append(lang)
            language_counts[lang] = language_counts.get(lang, 0) + 1
            code_file_count += 1
            code_paths.append(rel_norm)
        if compute_hashes and size <= 5 * 1024 * 1024:
            sha1 = hashlib.sha1(p.read_bytes()).hexdigest()
            entry["hash"] = f"sha1:{sha1}"
        file_entries.append(entry)

    # Entry points (heuristic by filename)
    entry_names = {
        "main.py",
        "__main__.py",
        "index.py",
        "index.js",
        "index.ts",
        "index.jsx",
        "index.tsx",
    }
    entrypoints = sorted([rel for rel in code_paths if Path(rel).name in entry_names])

    # Dependency graph and centrality
    graph = build_dep_graph(root)
    centrality_map = _centrality(graph)
    node_list = [
        {"path": n, "centrality": centrality_map[n]} for n in centrality_map
    ]
    node_list.sort(key=lambda x: (-x["centrality"], x["path"]))
    top_nodes = node_list[:5]

    # Test coverage heuristic
    test_files = {f for f in code_paths if f.startswith("tests/")}
    non_test_code = [f for f in code_paths if not f.startswith("tests/")]
    tested: set[str] = set()
    for cp in non_test_code:
        stem = Path(cp).stem
        ext = Path(cp).suffix
        candidates = {
            f"tests/test_{stem}{ext}",
            f"tests/{stem}_test{ext}",
            f"tests/{stem}.test{ext}",
            f"tests/{stem}.spec{ext}",
        }
        if candidates & test_files:
            tested.add(cp)
    tested_files = len(tested)
    untested_files = len(non_test_code) - tested_files
    coverage_pct = (
        tested_files / len(non_test_code) * 100 if non_test_code else 0.0
    )

    # CI tools summary
    ci = analysis_summarize_ci.summarize(root)
    ci_tools = {
        "gh_actions": ci["ci_tools"]["gh_actions"],
        "dockerfiles": ci["ci_tools"]["dockerfiles"],
        "python": ci["python"],
        "node": ci["node"],
        "notes": ci["notes"],
    }

    # Services
    rules = _read_codeowners(root)
    services: list[dict[str, object]] = []
    for svc in _service_candidates(root, non_test_code):
        svc_files = [p for p in non_test_code if p.startswith(f"{svc}/")]
        languages = sorted({
            _lang_for_path(root / p) for p in svc_files if _lang_for_path(root / p)
        })
        svc_set = set(svc_files)
        deps_in: set[str] = set()
        deps_out: set[str] = set()
        for src, dsts in graph.items():
            if src in svc_set:
                for dst in dsts:
                    if dst not in svc_set:
                        deps_out.add(dst)
            else:
                for dst in dsts:
                    if dst in svc_set:
                        deps_in.add(src)
        no_tests = sorted(Path(f).name for f in svc_files if f not in tested)
        high_cent = sorted(
            Path(f).name
            for f in svc_files
            if centrality_map.get(f, 0) > 0.5
        )
        service = {
            "name": Path(svc).name,
            "path": svc,
            "languages": languages,
            "files": len(svc_files),
            "deps_in": sorted(deps_in),
            "deps_out": sorted(deps_out),
            "owners": [],
            "risks": {
                "no_tests": no_tests,
                "high_centrality": high_cent,
            },
        }
        service_path = service["path"].replace("\\", "/")
        service["path"] = service_path
        service["owners"] = _owners_for(service_path, rules) if rules else []
        services.append(service)
    services.sort(key=lambda x: x["path"])

    data = {
        "version": "0.2.0",
        "root": str(root),
        "detected_languages": sorted(set(detected)),
        "language_counts": language_counts,
        "files": file_entries,
        "stats": {
            "file_count": len(file_entries),
            "code_file_count": code_file_count,
        },
        "entrypoints": entrypoints,
        "top_centrality_nodes": top_nodes,
        "test_coverage_summary": {
            "tested_files": tested_files,
            "untested_files": untested_files,
            "coverage_pct": round(coverage_pct, 2),
        },
        "ci_tools": ci_tools,
        "services": services,
    }
    return data


def save_repo_map(data: dict, outpath: Path) -> None:
    outpath.parent.mkdir(parents=True, exist_ok=True)
    outpath.write_text(json.dumps(data, indent=2))
