from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path

from silhouette_core.lang.js_parser import parse_js_ts

_JS_EXTS = {'.js', '.jsx', '.ts', '.tsx'}


def _iter_code_files(root: Path) -> Iterable[Path]:
    for p in root.rglob('*'):
        if p.is_file() and p.suffix.lower() in _JS_EXTS.union({'.py'}) and 'node_modules' not in p.parts:
            yield p


def _parse_python_imports(text: str, file_path: Path, root: Path) -> set[str]:
    imports: set[str] = set()
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                cand = root / (alias.name.replace('.', '/') + '.py')
                if cand.is_file():
                    imports.add(cand.relative_to(root).as_posix())
        elif isinstance(node, ast.ImportFrom):
            mod = '' if node.module is None else node.module
            base = file_path.parent
            if node.level:
                for _ in range(node.level - 1):
                    base = base.parent
            cand = base / (mod.replace('.', '/') + '.py')
            if cand.is_file():
                imports.add(cand.relative_to(root).as_posix())
    return imports


def _resolve_js_import(spec: str, src_dir: Path, root: Path) -> str | None:
    if not spec.startswith('.'):
        return None
    base = (src_dir / spec).resolve()
    if base.is_file():
        return base.relative_to(root).as_posix()
    for ext in _JS_EXTS:
        cand = Path(str(base) + ext)
        if cand.is_file():
            return cand.relative_to(root).as_posix()
    return None


def build_dep_graph(root: Path) -> dict[str, set[str]]:
    """Return a dependency graph mapping files to imported files."""
    root = root.resolve()
    graph: dict[str, set[str]] = {}
    for path in _iter_code_files(root):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding='utf-8')
        deps: set[str] = set()
        if path.suffix == '.py':
            deps = _parse_python_imports(text, path, root)
        else:
            parsed = parse_js_ts(rel, text)
            for imp in parsed['imports']:
                resolved = _resolve_js_import(imp['src'], path.parent, root)
                if resolved:
                    deps.add(resolved)
        graph[rel] = deps
    return graph
