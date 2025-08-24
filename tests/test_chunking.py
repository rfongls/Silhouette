from pathlib import Path
from silhouette_core.chunking import chunk_python, chunk_js_ts, chunk_fallback


def test_python_chunking_boundaries_and_overlap():
    text = (
        "def a():\n    pass\n\n\n"
        "def b():\n    pass\n"
    )
    chunks = chunk_python(text, max_lines=4, overlap=1, file_path="foo.py")
    assert chunks[0]["end_line"] == 4
    assert chunks[0]["end_line"] - chunks[1]["start_line"] == 1
    assert chunks == chunk_python(text, max_lines=4, overlap=1, file_path="foo.py")


def test_js_ts_chunking_and_determinism():
    text = Path("tests/fixtures/js_ts_repo/pkg/index.ts").read_text()
    chunks = chunk_js_ts(text, max_lines=3, overlap=1, file_path="index.ts")
    assert chunks[0]["end_line"] == 2
    assert chunks == chunk_js_ts(text, max_lines=3, overlap=1, file_path="index.ts")


def test_fallback_line_endings_and_determinism():
    text = "a\nb\nc\n" * 3
    text_crlf = text.replace("\n", "\r\n")
    chunks1 = chunk_fallback(text, max_lines=2, overlap=1, file_path="x.txt")
    chunks2 = chunk_fallback(text_crlf, max_lines=2, overlap=1, file_path="x.txt")
    coords1 = [(c["start_line"], c["end_line"]) for c in chunks1]
    coords2 = [(c["start_line"], c["end_line"]) for c in chunks2]
    assert coords1 == coords2
    assert chunks1 == chunk_fallback(text, max_lines=2, overlap=1, file_path="x.txt")
