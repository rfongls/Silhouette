from silhouette_core import selfcheck_engine as sce
from pathlib import Path


def test_check_files_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    missing = sce.check_files()
    assert set(missing) == {"persona.dsl", "memory.jsonl"}


def test_check_memory_valid(tmp_path):
    mem = tmp_path / "memory.jsonl"
    mem.write_text('{"role": "user", "content": "hi"}\n')
    assert sce.check_memory(mem) == []
