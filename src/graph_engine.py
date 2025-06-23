"""Conversation memory graph engine."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from itertools import combinations


def _parse_entry(raw: str) -> dict:
    data = json.loads(raw)
    if "timestamp" in data:
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
    return data


def build_graph(memory_path: str | Path = "logs/memory.jsonl") -> dict:
    """Build a graph of memory entries with simple linking rules."""
    path = Path(memory_path)
    if not path.exists():
        return {}

    entries: list[tuple[str, dict]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            entry = _parse_entry(line)
            node_id = uuid.uuid4().hex
            entries.append((node_id, entry))

    graph: dict[str, dict] = {nid: {"entry": entry, "links": []} for nid, entry in entries}

    for (id1, e1), (id2, e2) in combinations(entries, 2):
        same_intent = e1.get("intent") == e2.get("intent")
        close_time = False
        if "timestamp" in e1 and "timestamp" in e2:
            diff = abs((e1["timestamp"] - e2["timestamp"]).total_seconds())
            close_time = diff <= 600
        same_tone = e1.get("tone") == e2.get("tone")
        if same_intent or close_time or same_tone:
            graph[id1]["links"].append(id2)
            graph[id2]["links"].append(id1)

    return graph


def query_graph(graph: dict, node_id: str, depth: int = 1) -> list:
    """Return node ids connected to the start node within ``depth`` hops."""
    if node_id not in graph:
        return []
    visited = {node_id}
    frontier = [node_id]
    for _ in range(depth):
        next_frontier: list[str] = []
        for nid in frontier:
            for neigh in graph[nid]["links"]:
                if neigh not in visited:
                    visited.add(neigh)
                    next_frontier.append(neigh)
        frontier = next_frontier
        if not frontier:
            break
    return list(visited)


def summarize_thread(start_id: str, graph: dict) -> str:
    """Create a simple concatenated summary of related entries."""
    visited = set()
    queue = [start_id]
    texts: list[str] = []
    while queue:
        nid = queue.pop(0)
        if nid in visited or nid not in graph:
            continue
        visited.add(nid)
        entry = graph[nid]["entry"]
        text = entry.get("text")
        if text:
            texts.append(text)
        queue.extend(graph[nid]["links"])
    return " ".join(texts)

