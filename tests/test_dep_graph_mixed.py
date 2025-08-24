from pathlib import Path

from silhouette_core.graph.dep_graph import build_dep_graph


def test_dep_graph_mixed():
    root = Path('tests/fixtures/js_ts_repo')
    graph = build_dep_graph(root)
    edges = {(src, dst) for src, deps in graph.items() for dst in deps}
    assert ('pkg/index.ts', 'pkg/util.ts') in edges
    assert ('pkg/a.js', 'pkg/b.jsx') in edges
    assert ('pkg/py_main.py', 'pkg/py_helper.py') in edges
    assert ('pkg/index.ts', 'pkg/types.ts') not in edges
    # Ensure all files represented
    assert set(graph.keys()) >= {
        'pkg/index.ts', 'pkg/util.ts', 'pkg/a.js', 'pkg/b.jsx',
        'pkg/py_main.py', 'pkg/py_helper.py'
    }
