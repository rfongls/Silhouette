from __future__ import annotations

import ast
import hashlib
import re

_MAX_CHARS = 10000

def _normalize_newlines(text: str) -> str:
    return text.replace('\r\n', '\n').replace('\r', '\n')

def _make_chunk_id(file_path: str, start: int, end: int, commit_sha: str | None) -> str:
    base = f"{file_path}:{start}:{end}"
    if commit_sha:
        base += f":{commit_sha}"
    return hashlib.sha1(base.encode()).hexdigest()

def _window_chunks(lines: list[str], *, max_lines: int, overlap: int,
                   file_path: str, commit_sha: str | None) -> list[dict]:
    chunks: list[dict] = []
    start = 1
    n = len(lines)
    while start <= n:
        end = min(start + max_lines - 1, n)
        text = '\n'.join(lines[start - 1:end])
        while len(text) > _MAX_CHARS and end > start:
            end -= 1
            text = '\n'.join(lines[start - 1:end])
        chunk_id = _make_chunk_id(file_path, start, end, commit_sha)
        chunks.append({"id": chunk_id, "start_line": start, "end_line": end, "text": text})
        if end == n:
            break
        new_start = end - overlap
        if new_start <= start:
            new_start = end + 1
        start = new_start
    return chunks

def chunk_fallback(text: str, *, max_lines: int = 180, overlap: int = 30,
                   file_path: str = "", commit_sha: str | None = None) -> list[dict]:
    """Pure windowing with deterministic overlap; no AST knowledge."""
    normalized = _normalize_newlines(text)
    lines = normalized.split('\n')
    return _window_chunks(lines, max_lines=max_lines, overlap=overlap,
                          file_path=file_path, commit_sha=commit_sha)

def chunk_python(text: str, *, max_lines: int = 180, overlap: int = 30,
                 file_path: str = "", commit_sha: str | None = None) -> list[dict]:
    """
    Prefer splitting at def/class boundaries (via ast); fallback to line windows.
    Return items like:
    {"id": "sha1:...", "start_line": 1, "end_line": 180, "text": "..."}
    """
    normalized = _normalize_newlines(text)
    try:
        tree = ast.parse(normalized)
        boundaries = sorted({
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
        })
    except SyntaxError:
        boundaries = []
    lines = normalized.split('\n')
    if not boundaries:
        return _window_chunks(lines, max_lines=max_lines, overlap=overlap,
                              file_path=file_path, commit_sha=commit_sha)
    chunks: list[dict] = []
    start = 1
    n = len(lines)
    while start <= n:
        tentative_end = min(start + max_lines - 1, n)
        cut = None
        for b in boundaries:
            if start < b <= tentative_end:
                cut = b - 1
        end = cut if cut is not None and cut >= start else tentative_end
        text_chunk = '\n'.join(lines[start - 1:end])
        while len(text_chunk) > _MAX_CHARS and end > start:
            end -= 1
            text_chunk = '\n'.join(lines[start - 1:end])
        chunk_id = _make_chunk_id(file_path, start, end, commit_sha)
        chunks.append({"id": chunk_id, "start_line": start, "end_line": end, "text": text_chunk})
        if end == n:
            break
        new_start = end - overlap
        if new_start <= start:
            new_start = end + 1
        start = new_start
    return chunks

def chunk_js_ts(text: str, *, max_lines: int = 180, overlap: int = 30,
                file_path: str = "", commit_sha: str | None = None) -> list[dict]:
    """
    Prefer splitting at function/arrow/class boundaries. Fallback to line windows.
    Same return schema as above.
    """
    normalized = _normalize_newlines(text)
    # crude boundary detection using regex patterns
    pattern = re.compile(r"^\s*(?:export\s+)?(?:function|class|const|let|var)\b.*")
    lines = normalized.split('\n')
    boundaries = []
    for i, line in enumerate(lines, start=1):
        if pattern.match(line):
            boundaries.append(i)
    if not boundaries:
        return _window_chunks(lines, max_lines=max_lines, overlap=overlap,
                              file_path=file_path, commit_sha=commit_sha)
    chunks: list[dict] = []
    start = 1
    n = len(lines)
    while start <= n:
        tentative_end = min(start + max_lines - 1, n)
        cut = None
        for b in boundaries:
            if start < b <= tentative_end:
                cut = b - 1
        end = cut if cut is not None and cut >= start else tentative_end
        text_chunk = '\n'.join(lines[start - 1:end])
        while len(text_chunk) > _MAX_CHARS and end > start:
            end -= 1
            text_chunk = '\n'.join(lines[start - 1:end])
        chunk_id = _make_chunk_id(file_path, start, end, commit_sha)
        chunks.append({"id": chunk_id, "start_line": start, "end_line": end, "text": text_chunk})
        if end == n:
            break
        new_start = end - overlap
        if new_start <= start:
            new_start = end + 1
        start = new_start
    return chunks
