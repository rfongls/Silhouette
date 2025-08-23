import pytest

from silhouette_core.repo_adapter import LocalRepoAdapter


def test_local_repo_adapter_basic(tmp_path):
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    (tmp_path / "b.py").write_text("print('hi')\n", encoding="utf-8")

    adapter = LocalRepoAdapter(tmp_path)
    adapter.fetch(str(tmp_path))

    files = adapter.list_files(["**/*.py", "**/*.txt"])
    assert files == sorted(["a.txt", "b.py"])

    assert adapter.read_text("a.txt") == "hello"

    with pytest.raises(PermissionError):
        adapter.write_text("new.txt", "data")
