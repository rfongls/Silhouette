from silhouette_core.distiller import (
    summarize_memory,
    extract_embeddings,
    distill,
)


def test_summarize_memory(tmp_path):
    mem = tmp_path / "memory.jsonl"
    mem.write_text('{"content": "a"}\n{"content": "b"}\n')
    summary = summarize_memory(mem, limit=1)
    assert summary["entries"] == 2
    assert summary["core"] == ["a"]


def test_extract_embeddings(tmp_path):
    mem = tmp_path / "memory.jsonl"
    mem.write_text('{"content": "abc"}\n')
    emb = extract_embeddings(mem, limit=1, bits=4)
    assert len(emb) == 1
    assert len(emb[0]) == 2


def test_distill(tmp_path):
    persona = tmp_path / "persona.dsl"
    persona.write_text("[values]\nrule=1")
    mem = tmp_path / "memory.jsonl"
    mem.write_text('{"content": "hi"}\n')
    cfg = tmp_path / "dist.yml"
    cfg.write_text("summary_length: 1\nquantization_bits: 4\n")
    result = distill(persona, mem, cfg)
    assert result["summary"]["entries"] == 1
    assert result["embeddings"]

