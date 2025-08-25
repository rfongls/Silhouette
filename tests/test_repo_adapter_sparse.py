from __future__ import annotations
from pathlib import Path
import subprocess, sys
import pytest

pytestmark = pytest.mark.skipif(sys.platform.startswith("win"), reason="git sparse-checkout suite is flaky on Windows CI")


def _git_init(repo: Path):
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (repo / "src").mkdir()
    (repo / "src" / "a.py").write_text("print('a')\n")
    (repo / "notes.txt").write_text("n\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return repo


def test_sparse_list_minimal(tmp_path: Path):
    repo = _git_init(tmp_path / "r")
    work = tmp_path / "work"
    try:
        from silhouette_core.repo_adapter_git import GitRepoAdapter as Adapter
    except Exception:
        from silhouette_core.repo_adapter import RepoAdapter as Adapter  # pragma: no cover
    a = Adapter(workdir=work)
    a.fetch(str(repo), sparse=["src"])
    files = a.list_files(["**/*"])
    assert "src/a.py" in files
    assert "notes.txt" not in files
