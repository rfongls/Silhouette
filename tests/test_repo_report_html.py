from __future__ import annotations

from pathlib import Path

from silhouette_core.repo_map import build_repo_map
from silhouette_core.report.html_report import render_repo_map_html


def _collect_files(root: Path) -> list[str]:
    return [str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()]


def test_html_report_sections(tmp_path):
    root = Path("tests/fixtures/mixed_repo").resolve()
    files = _collect_files(root)
    data = build_repo_map(root, files)

    html_path = tmp_path / "report.html"
    render_repo_map_html(data, html_path)
    text = html_path.read_text(encoding="utf-8")
    assert "<section id=\"overview\">" in text
    assert "<section id=\"hotspots\">" in text
    assert "<section id=\"services\">" in text
    assert "services/api" in text
    assert "@team-api" in text or "none" in text
    assert '<a href="repo_map.json"' in text

    html_path2 = tmp_path / "report2.html"
    render_repo_map_html(data, html_path2)
    assert text == html_path2.read_text(encoding="utf-8")
