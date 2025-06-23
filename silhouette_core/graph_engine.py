import json
import uuid

def build_graph(memory_path="logs/memory.jsonl"):
    with open(memory_path, "r") as f:
        entries = [json.loads(line) for line in f]
    graph = {}
    for i, entry in enumerate(entries):
        node_id = entry.get("id", str(uuid.uuid4()))
        entry["id"] = node_id
        graph.setdefault(node_id, {"entry": entry, "links": []})

    for i, e1 in enumerate(entries):
        for j, e2 in enumerate(entries[i + 1 :], start=i + 1):
            if e1.get("intent") == e2.get("intent"):
                id1 = e1["id"]
                id2 = e2.setdefault("id", str(uuid.uuid4()))
                graph[id1]["links"].append(id2)
                graph.setdefault(id2, {"entry": e2, "links": []})
                graph[id2]["links"].append(id1)

    return graph


def query_graph(graph, start_id, depth=1):
    """Return node ids within given depth from start_id."""
    visited = set([start_id])
    frontier = [start_id]
    for _ in range(depth):
        next_frontier = []
        for node in frontier:
            for link in graph.get(node, {}).get("links", []):
                if link not in visited:
                    visited.add(link)
                    next_frontier.append(link)
        frontier = next_frontier
        if not frontier:
            break
    return visited

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
