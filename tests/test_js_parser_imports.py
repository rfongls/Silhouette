import silhouette_core.lang.js_parser as jp

def test_js_parser_imports():
    assert hasattr(jp, "parse_js_ts")
