from pathlib import Path

from silhouette_core.lang.js_parser import parse_js_ts

FIXTURE = Path('tests/fixtures/js_ts_repo')


def _parse(rel: str):
    text = (FIXTURE / rel).read_text(encoding='utf-8')
    return parse_js_ts(rel, text)


def test_parse_index_ts():
    data = _parse('pkg/index.ts')
    assert {"src": "./util", "symbols": []} in data["imports"]
    assert {"name": "foo", "kind": "function"} in data["exports"]


def test_parse_util_ts():
    data = _parse('pkg/util.ts')
    assert any(sym["name"] == "bar" for sym in data["symbols"])
    assert {"name": "bar", "kind": "function"} in data["exports"]


def test_parse_a_js():
    data = _parse('pkg/a.js')
    assert {"src": "./b", "symbols": []} in data["imports"]
    assert {"name": "x", "kind": "var"} in data["exports"]


def test_parse_b_jsx():
    data = _parse('pkg/b.jsx')
    assert {"src": "react", "symbols": []} in data["imports"]
    assert any(exp["name"] in {"default", "B"} for exp in data["exports"])
