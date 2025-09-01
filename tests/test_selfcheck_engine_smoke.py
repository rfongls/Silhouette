from __future__ import annotations
from silhouette_core import selfcheck_engine as sce


def test_selfcheck_main_smoke(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path/"persona.dsl").write_text("ok\n")
    (tmp_path/"memory.jsonl").write_text('{"role":"user","content":"hi"}\n')
    sce.main([])
    out = capsys.readouterr().out
    assert "All checks passed" in out
