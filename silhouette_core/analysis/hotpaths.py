from __future__ import annotations

from collections import defaultdict


def analyze(graph: dict[str, set[str]], top_n: int = 10) -> dict:
    indeg = defaultdict(int)
    for _src, dsts in graph.items():
        for dst in dsts:
            indeg[dst] += 1
    max_deg = 1
    centrality: dict[str, float] = {}
    for node, dsts in graph.items():
        deg = len(dsts) + indeg.get(node, 0)
        centrality[node] = deg
        if deg > max_deg:
            max_deg = deg
    for node in centrality:
        centrality[node] /= max_deg
    nodes = sorted(
        (
            {
                "path": node,
                "centrality": centrality[node],
                "recent_changes": 0,
            }
            for node in graph
        ),
        key=lambda x: x["centrality"],
        reverse=True,
    )
    return {"nodes": nodes[:top_n], "method": "degree", "commit": None}
