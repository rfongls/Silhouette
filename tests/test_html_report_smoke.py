from __future__ import annotations
from pathlib import Path
from silhouette_core.report.html_report import render_repo_map_html


def test_html_report_contains_sections(tmp_path: Path):
    repo_map = {
        "version": "0",
        "root": str(tmp_path),
        "detected_languages": ["py"],
        "language_counts": {"py": 1},
        "files": [{"path": "a.py", "size": 1}],
        "stats": {"file_count": 1, "code_file_count": 1},
        "entrypoints": ["a.py"],
        "top_centrality_nodes": [{"path": "a.py", "centrality": 1.0}],
        "test_coverage_summary": {"tested_files": 0, "untested_files": 1, "coverage_pct": 0.0},
        "ci_tools": {"gh_actions": False, "dockerfiles": []},
        "services": [
            {
                "name": "core",
                "path": "",
                "languages": ["py"],
                "files": 1,
                "deps_in": [],
                "deps_out": [],
                "owners": [],
                "risks": {},
            }
        ],
    }
    out = tmp_path/"repo_map.html"
    render_repo_map_html(repo_map, str(out))
    html = out.read_text(encoding="utf-8")
    html_lower = html.lower()
    assert "overview" in html_lower
    assert "services" in html_lower
    assert "hotspot" in html_lower or "centrality" in html_lower
