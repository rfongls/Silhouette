from unittest.mock import Mock

from silhouette_core.embedding_engine import EmbeddingIndex, StubEmbedder
from silhouette_core.chunking import chunk_fallback


def test_upsert_and_query(tmp_path):
    db = tmp_path / "emb.sqlite"
    index = EmbeddingIndex(db_path=str(db))
    text = "hello world\n" * 5
    chunks = chunk_fallback(text, max_lines=2, overlap=1, file_path="a.txt")
    index.upsert("a.txt", None, chunks)
    results = index.query("hello", top_k=1)
    assert results and results[0]["path"] == "a.txt"


def test_reindex_if_changed(tmp_path):
    db = tmp_path / "emb.sqlite"
    index = EmbeddingIndex(db_path=str(db))

    def build():
        return chunk_fallback("one two three", max_lines=2, overlap=1, file_path="f.txt")

    index.reindex_if_changed("f.txt", mtime=1.0, sha1="abc", build_chunks=build)
    mocked = Mock(wraps=build)
    index.reindex_if_changed("f.txt", mtime=1.0, sha1="abc", build_chunks=mocked)
    assert mocked.call_count == 0
    mocked2 = Mock(return_value=chunk_fallback("changed text", max_lines=2, overlap=1, file_path="f.txt"))
    index.reindex_if_changed("f.txt", mtime=2.0, sha1="def", build_chunks=mocked2)
    assert mocked2.call_count == 1


def test_stub_embedder_deterministic():
    emb = StubEmbedder()
    v1 = emb.embed_texts(["some text"])[0]
    v2 = emb.embed_texts(["some text"])[0]
    assert v1 == v2
