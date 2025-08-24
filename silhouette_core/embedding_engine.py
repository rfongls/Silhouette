from __future__ import annotations

import hashlib
import math
import os
import sqlite3
from array import array
from collections.abc import Callable


class Embedder:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover - interface
        raise NotImplementedError


class StubEmbedder(Embedder):
    """Offline, deterministic hash-based bag-of-words embedder."""

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vec = [0.0] * self.dim
            for word in text.lower().split():
                h = int(hashlib.sha1(word.encode()).hexdigest(), 16)
                vec[h % self.dim] += 1.0
            vectors.append(vec)
        return vectors


class EmbeddingIndex:
    def __init__(self, db_path: str = ".silhouette/embeddings.sqlite",
                 embedder: Embedder | None = None) -> None:
        self.db_path = db_path
        self.embedder = embedder or StubEmbedder()
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self) -> None:
        schema_path = os.path.join(os.path.dirname(__file__), "embedding_schema.sql")
        with open(schema_path, encoding="utf-8") as f:
            self.conn.executescript(f.read())
        self.conn.commit()

    def upsert(self, file_path: str, commit_sha: str | None,
               chunks: list[dict]) -> None:
        cur = self.conn.cursor()
        cur.execute("SELECT file_id FROM files WHERE path=?", (file_path,))
        row = cur.fetchone()
        if row:
            file_id = row[0]
        else:
            cur.execute("INSERT INTO files(path, commit_sha) VALUES(?, ?)", (file_path, commit_sha))
            file_id = cur.lastrowid
        cur.execute("UPDATE files SET commit_sha=? WHERE file_id=?", (commit_sha, file_id))
        cur.execute("SELECT chunk_id FROM chunks WHERE file_id=?", (file_id,))
        existing = {r[0] for r in cur.fetchall()}
        incoming = {c["id"] for c in chunks}
        to_remove = existing - incoming
        for cid in to_remove:
            cur.execute("DELETE FROM chunks WHERE chunk_id=?", (cid,))
            cur.execute("DELETE FROM vectors WHERE chunk_id=?", (cid,))
        texts = [c["text"] for c in chunks]
        vectors = self.embedder.embed_texts(texts)
        for chunk, vec in zip(chunks, vectors, strict=False):
            cur.execute(
                "REPLACE INTO chunks(chunk_id, file_id, start_line, end_line) VALUES(?, ?, ?, ?)",
                (chunk["id"], file_id, chunk["start_line"], chunk["end_line"]),
            )
            cur.execute(
                "REPLACE INTO vectors(chunk_id, dim, data) VALUES(?, ?, ?)",
                (chunk["id"], len(vec), array("f", vec).tobytes()),
            )
        self.conn.commit()

    def _cosine(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b, strict=False))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if not norm_a or not norm_b:
            return 0.0
        return dot / (norm_a * norm_b)

    def query(self, text: str, top_k: int = 10) -> list[dict]:
        qvec = self.embedder.embed_texts([text])[0]
        cur = self.conn.cursor()
        cur.execute(
            "SELECT chunks.chunk_id, files.path, chunks.start_line, chunks.end_line, vectors.dim, vectors.data "
            "FROM chunks JOIN files ON chunks.file_id = files.file_id "
            "JOIN vectors ON vectors.chunk_id = chunks.chunk_id"
        )
        results: list[dict] = []
        for row in cur.fetchall():
            cid, path, start, end, dim, data = row
            vec = array("f")
            vec.frombytes(data)
            score = self._cosine(qvec, vec.tolist())
            results.append({
                "chunk_id": cid,
                "path": path,
                "start_line": start,
                "end_line": end,
                "score": score,
            })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def reindex_if_changed(self, file_path: str, mtime: float, sha1: str,
                           build_chunks: Callable[[], list[dict]], commit_sha: str | None = None) -> None:
        cur = self.conn.cursor()
        cur.execute("SELECT file_id, last_mtime, last_sha1 FROM files WHERE path=?", (file_path,))
        row = cur.fetchone()
        if row and row[1] == mtime and row[2] == sha1:
            return
        chunks = build_chunks()
        self.upsert(file_path, commit_sha, chunks)
        cur.execute("SELECT file_id FROM files WHERE path=?", (file_path,))
        file_id = cur.fetchone()[0]
        cur.execute(
            "UPDATE files SET last_mtime=?, last_sha1=?, commit_sha=? WHERE file_id=?",
            (mtime, sha1, commit_sha, file_id),
        )
        self.conn.commit()
