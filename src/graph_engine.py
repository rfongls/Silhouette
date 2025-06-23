import json
import uuid
from datetime import datetime, timedelta

def build_graph(memory_path="logs/memory.jsonl"):
    with open(memory_path, "r") as f:
        entries = [json.loads(line) for line in f]
    graph = {}
    for i, entry in enumerate(entries):
        node_id = entry.get("id", str(uuid.uuid4()))
        entry["id"] = node_id
        links = []
        for j in range(max(0, i-3), i):  # last 3 entries before current
            if abs(i - j) <= 3:
                links.append(entries[j]["id"])
        graph[node_id] = {"entry": entry, "links": links}
    return graph

def summarize_thread(start_id, graph, depth=1):
    visited = set()
    summary = []

    def dfs(node_id, d):
        if d > depth or node_id in visited:
            return
        visited.add(node_id)
        entry = graph[node_id]["entry"]
        if "text" in entry:
            summary.append(entry["text"])
        for link in graph[node_id]["links"]:
            dfs(link, d + 1)

    dfs(start_id, 0)
    return " → ".join(reversed(summary))
