from __future__ import annotations
from pathlib import Path
import subprocess
import sys
import json
import time
import os

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

    assert "http://" not in text and "https://" not in text
    assert "<link" not in text

    html_path2 = tmp_path / "report2.html"
    render_repo_map_html(data, html_path2)
    assert text == html_path2.read_text(encoding="utf-8")


def test_repo_map_cli_html_determinism_and_flags(tmp_path):
    src = Path("tests/fixtures/mixed_repo").resolve()
    cmd = [
        sys.executable,
        "-m",
        "silhouette_core.cli",
        "repo",
        "map",
        str(src),
        "--json-out",
        "repo_map.json",
    ]

    env = {**os.environ, "PYTHONPATH": str(Path.cwd())}
    subprocess.run(cmd, cwd=tmp_path, check=True, env=env)
    artifacts_dir = tmp_path / "artifacts"
    dirs = sorted(artifacts_dir.iterdir())
    first = dirs[0]
    html1 = (first / "repo_map.html").read_text(encoding="utf-8")
    run_meta = json.loads((first / "silhouette_run.json").read_text(encoding="utf-8"))
    assert run_meta["args"]["html_out"] == "repo_map.html"

    time.sleep(1)
    subprocess.run(cmd, cwd=tmp_path, check=True, env=env)
    dirs = sorted(artifacts_dir.iterdir())
    second = dirs[1]
    html2 = (second / "repo_map.html").read_text(encoding="utf-8")
    assert html1 == html2
    assert "http://" not in html1 and "https://" not in html1 and "<link" not in html1

    time.sleep(1)
    cmd_no_html = cmd + ["--no-html"]
    subprocess.run(cmd_no_html, cwd=tmp_path, check=True, env=env)
    dirs = sorted(artifacts_dir.iterdir())
    third = dirs[2]
    assert not (third / "repo_map.html").exists()
    run_meta3 = json.loads((third / "silhouette_run.json").read_text(encoding="utf-8"))
    assert run_meta3["args"]["html_out"] is None
