from __future__ import annotations

from pathlib import Path

import yaml

from silhouette_core.chunking import chunk_js_ts, chunk_python
from silhouette_core.embedding_engine import EmbeddingIndex
from silhouette_core.retrieval.planner import RetrievalPlanner


def _build_graph(root: Path) -> dict[str, set[str]]:
    return {
        "services/api/validators.ts": set(),
        "services/api/routes.ts": {"services/api/validators.ts"},
        "hl7/msh_builder.py": set(),
    }


def _build_index(root: Path) -> EmbeddingIndex:
    idx = EmbeddingIndex(db_path=str(root / ".silhouette" / "embeddings.sqlite"))
    for path in root.rglob("*.py"):
        rel = path.relative_to(root).as_posix()
        idx.upsert(rel, None, chunk_python(path.read_text(encoding="utf-8")))
    for path in root.rglob("*.ts"):
        rel = path.relative_to(root).as_posix()
        idx.upsert(rel, None, chunk_js_ts(path.read_text(encoding="utf-8")))
    return idx


def test_retrieval_planner_precision_recall(tmp_path):
    repo = Path("tests/fixtures/mixed_repo").resolve()
    graph = _build_graph(repo)
    index = _build_index(repo)
    planner = RetrievalPlanner(graph, index, alpha=0.5, seed=0)
    goldens = yaml.safe_load(Path("tests/goldens/retrieval_qa.yaml").read_text())
    for g in goldens:
        res1 = planner.rank_targets(g["query"], top_k=3)
        res2 = planner.rank_targets(g["query"], top_k=3)
        assert res1 == res2
        paths = [r["path"] for r in res1]
        hits = [p for p in paths if p in g["relevant"]]
        precision = len(hits) / 3
        recall = len(hits) / len(g["relevant"])
        assert precision >= 0.3
        assert recall >= 0.5
