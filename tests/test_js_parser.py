from pathlib import Path

from silhouette_core.lang.js_parser import parse_js_ts

FIXTURE = Path('tests/fixtures/js_ts_repo')


def _parse(rel: str):
    text = (FIXTURE / rel).read_text(encoding='utf-8')
    return parse_js_ts(rel, text)


def test_parse_index_ts():
    data = _parse('pkg/index.ts')
    assert {"src": "./util", "symbols": []} in data["imports"]
    assert all(imp["src"] != "./types" for imp in data["imports"])
    exp = {(e["name"], e["kind"]) for e in data["exports"]}
    assert ("foo", "function") in exp
    assert ("FooDefault", "function") in exp
    assert ("arrow", "var") in exp
    assert ("arrow2", "var") in exp
    assert ("decorated", "function") in exp
    sym_map = {s["name"]: s["loc"] for s in data["symbols"]}
    assert sym_map["foo"] == {"line": 3, "column": 8}
    assert sym_map["FooDefault"] == {"line": 4, "column": 16}
    assert sym_map["decorated"] == {"line": 8, "column": 8}
    assert sym_map["declaredFunc"] == {"line": 9, "column": 9}
    assert sym_map["localFunc"] == {"line": 10, "column": 1}


def test_parse_util_ts():
    data = _parse('pkg/util.ts')
    sym = next(sym for sym in data["symbols"] if sym["name"] == "bar")
    assert sym["loc"] == {"line": 1, "column": 8}
    assert {"name": "bar", "kind": "function"} in data["exports"]


def test_parse_a_js():
    data = _parse('pkg/a.js')
    assert {"src": "./b", "symbols": []} in data["imports"]
    assert {"src": "fs", "symbols": []} in data["imports"]
    assert {"name": "x", "kind": "var"} in data["exports"]


def test_parse_b_jsx():
    data = _parse('pkg/b.jsx')
    assert {"src": "react", "symbols": []} in data["imports"]
    assert {"name": "default", "kind": "function"} in data["exports"]


def test_crlf_newlines():
    text = "export function foo() {}\r\nfunction bar() {}\r\n"
    data = parse_js_ts('mem.js', text)
    sym_map = {s["name"]: s["loc"] for s in data["symbols"]}
    assert sym_map["foo"] == {"line": 1, "column": 8}
    assert sym_map["bar"] == {"line": 2, "column": 1}
