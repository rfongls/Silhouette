import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def _create_memory_file(path):
    entries = [
        {
            "timestamp": "2023-01-01T00:00:00",
            "text": "Hello",
            "intent": "greet",
            "tone": "positive",
        },
        {
            "timestamp": "2023-01-01T00:05:00",
            "text": "Hi",
            "intent": "greet",
            "tone": "positive",
        },
        {
            "timestamp": "2023-01-01T01:00:00",
            "text": "Angry message",
            "intent": "complain",
            "tone": "negative",
        },
    ]
    with open(path, "w", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(e) + "\n")
    return entries


def test_build_graph_creates_expected_links(tmp_path):
    import graph_engine

    mem_file = tmp_path / "mem.jsonl"
    _create_memory_file(mem_file)

    graph = graph_engine.build_graph(mem_file)
    assert len(graph) == 3

    # find node ids by text
    ids = {v["entry"]["text"]: k for k, v in graph.items()}
    id1 = ids["Hello"]
    id2 = ids["Hi"]
    id3 = ids["Angry message"]

    assert id2 in graph[id1]["links"]
    assert id1 in graph[id2]["links"]
    assert id3 not in graph[id1]["links"]
    assert id3 not in graph[id2]["links"]


def test_query_graph_returns_neighbors(tmp_path):
    import graph_engine

    mem_file = tmp_path / "mem.jsonl"
    _create_memory_file(mem_file)
    graph = graph_engine.build_graph(mem_file)
    id_hello = next(k for k, v in graph.items() if v["entry"]["text"] == "Hello")

    nodes = graph_engine.query_graph(graph, id_hello, depth=1)
    texts = {graph[n]["entry"]["text"] for n in nodes}
    assert "Hello" in texts and "Hi" in texts and "Angry message" not in texts


def test_summarize_thread_joins_content(tmp_path):
    import graph_engine

    mem_file = tmp_path / "mem.jsonl"
    _create_memory_file(mem_file)
    graph = graph_engine.build_graph(mem_file)
    id_hello = next(k for k, v in graph.items() if v["entry"]["text"] == "Hello")
    summary = graph_engine.summarize_thread(id_hello, graph)
    assert "Hello" in summary
    assert "Hi" in summary
    assert "Angry message" not in summary

