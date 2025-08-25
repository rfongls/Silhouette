from __future__ import annotations
from silhouette_core.chunking import chunk_fallback, chunk_python, chunk_js_ts

PY_TEXT = """\
def a(x):
    return x + 1

class C:
    def m(self):
        return 42
"""

TS_TEXT = """\
// named function
export function foo(x:number){ return x+1; }
// arrow
export const bar = (y:number) => y+2;
// default anonymous
export default function(z){ return z+3; }
"""

def _windows(chunks):
    return [(c["start_line"], c["end_line"]) for c in chunks]

def test_chunk_fallback_is_deterministic_and_overlaps():
    c1 = chunk_fallback("line\n" * 500, max_lines=120, overlap=20)
    c2 = chunk_fallback("line\n" * 500, max_lines=120, overlap=20)
    assert _windows(c1) == _windows(c2)
    if len(c1) >= 2:
        (s0, e0), (s1, e1) = _windows(c1)[:2]
        assert s1 <= e0  # overlap honored

def test_chunk_python_determinism():
    c1 = chunk_python(PY_TEXT, max_lines=40, overlap=10)
    c2 = chunk_python(PY_TEXT, max_lines=40, overlap=10)
    assert c1 and c2
    assert _windows(c1) == _windows(c2)

def test_chunk_js_ts_determinism():
    c1 = chunk_js_ts(TS_TEXT, max_lines=40, overlap=10)
    c2 = chunk_js_ts(TS_TEXT, max_lines=40, overlap=10)
    assert c1 and c2
    assert _windows(c1) == _windows(c2)
