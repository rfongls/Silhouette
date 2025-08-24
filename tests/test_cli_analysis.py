import json
import os
import subprocess
import sys
from pathlib import Path


def _run(repo: Path, *args: str):
    cmd = [sys.executable, "-m", "silhouette_core.cli", *args, "--json"]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    out = subprocess.check_output(cmd, cwd=repo, env=env)
    return json.loads(out)


def test_hotpaths():
    repo = Path("tests/fixtures/mixed_repo")
    data = _run(repo, "analyze", "hotpaths")
    assert "nodes" in data and data["nodes"]


def test_service():
    repo = Path("tests/fixtures/mixed_repo")
    data = _run(repo, "analyze", "service", "services/api")
    assert "@team-api" in data.get("owners", [])


def test_suggest_tests():
    repo = Path("tests/fixtures/mixed_repo")
    data = _run(repo, "suggest", "tests", ".")
    assert data.get("targets")


def test_summarize_ci():
    repo = Path("tests/fixtures/mixed_repo")
    data = _run(repo, "summarize", "ci")
    assert data["ci_tools"]["gh_actions"]
    assert "ruff" in data["python"]["lint"]
    assert "pytest" in data["python"]["test"]
