from __future__ import annotations

import collections
import random
import re


class RetrievalPlanner:
    def __init__(self, graph: dict[str, set[str]], index, *, alpha: float = 0.5, seed: int = 0) -> None:
        self.graph = graph
        self.index = index
        self.alpha = alpha
        self.random = random.Random(seed)
        self._build_graph_helpers()

    def _build_graph_helpers(self) -> None:
        indeg: dict[str, int] = collections.defaultdict(int)
        undirected: dict[str, set[str]] = collections.defaultdict(set)
        for src, dsts in self.graph.items():
            for dst in dsts:
                indeg[dst] += 1
                undirected[src].add(dst)
                undirected[dst].add(src)
        deg: dict[str, int] = {}
        max_deg = 1
        for node, dsts in self.graph.items():
            d = len(dsts) + indeg.get(node, 0)
            deg[node] = d
            if d > max_deg:
                max_deg = d
        self.centrality = {n: d / max_deg for n, d in deg.items()}
        self.undirected = undirected

    def _bfs_distance(self, starts: list[str]) -> dict[str, int]:
        dist: dict[str, int] = {s: 0 for s in starts}
        queue = collections.deque(starts)
        while queue:
            node = queue.popleft()
            for nb in self.undirected.get(node, set()):
                if nb not in dist:
                    dist[nb] = dist[node] + 1
                    queue.append(nb)
        return dist

    def rank_targets(self, query: str, top_k: int = 15) -> list[dict]:
        tokens = [t for t in re.split(r"\W+", query.lower()) if t]
        matched_nodes = [n for n in self.graph if any(t in n.lower() for t in tokens)]
        embed_hits = self.index.query(query, top_k=top_k)
        embed_map: dict[str, float] = {}
        for hit in embed_hits:
            path = hit["path"]
            score = hit["score"]
            embed_map[path] = max(embed_map.get(path, 0.0), score)
        candidates = set(matched_nodes) | set(embed_map.keys())
        if not candidates:
            candidates = set(self.graph.keys())
        dist = self._bfs_distance(matched_nodes) if matched_nodes else {}
        results: list[dict] = []
        for node in candidates:
            embed_score = embed_map.get(node, 0.0)
            prox = 1.0 / (1 + dist[node]) if node in dist else 0.0
            graph_score = max(self.centrality.get(node, 0.0), prox)
            final = (1 - self.alpha) * graph_score + self.alpha * embed_score
            results.append(
                {
                    "path": node,
                    "symbol": "",
                    "score": final,
                    "why": {
                        "graph": graph_score,
                        "embed": embed_score,
                        "neighbors": sorted(self.graph.get(node, set())),
                    },
                }
            )
        results.sort(key=lambda x: (-x["score"], x["path"], x["symbol"]))
        return results[:top_k]
