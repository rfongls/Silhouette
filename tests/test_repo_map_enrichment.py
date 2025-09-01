from __future__ import annotations

from pathlib import Path

from silhouette_core.repo_map import build_repo_map


def _collect_files(root: Path) -> list[str]:
    return [str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()]


def test_repo_map_enrichment():
    root = Path("tests/fixtures/mixed_repo").resolve()
    files = _collect_files(root)
    data = build_repo_map(root, files)

    assert isinstance(data["entrypoints"], list)
    assert data["top_centrality_nodes"], "centrality nodes should be present"
    assert "coverage_pct" in data["test_coverage_summary"]

    ci = data["ci_tools"]
    for key in ["gh_actions", "dockerfiles", "python", "node"]:
        assert key in ci

    services = data["services"]
    paths = [s["path"] for s in services]
    assert paths == sorted(paths)
    svc_api = next(s for s in services if s["path"] == "services/api")
    assert svc_api["owners"] == ["@team-api"]
    assert "risks" in svc_api
