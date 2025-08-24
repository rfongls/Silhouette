from __future__ import annotations

import re

# Simple regex-based parser for JS/TS files. It is intentionally
# lightweight and covers the import/export forms used in tests. It does
# not aim for full ECMAScript compliance but keeps parsing deterministic
# and offline-friendly.

IMPORT_RE = re.compile(
    r"(?:import[^'\";]+from\s*['\"]([^'\"]+)['\"]|require\(\s*['\"]([^'\"]+)['\"]\s*\))"
)
EXPORT_FUNC_RE = re.compile(r"export\s+function\s+(\w+)")
EXPORT_DEFAULT_FUNC_RE = re.compile(r"export\s+default\s+function\s*(\w+)?")
EXPORT_CONST_RE = re.compile(r"export\s+const\s+(\w+)\s*=")
EXPORT_LIST_RE = re.compile(r"export\s*{([^}]+)}")
MODULE_EXPORTS_RE = re.compile(r"module\.exports\s*=\s*{([^}]+)}")
FUNC_DECL_RE = re.compile(r"function\s+(\w+)")


def parse_js_ts(file_path: str, text: str) -> dict:
    """Parse a JS/TS file into imports/exports/symbols."""
    # Normalise newlines so that CRLF and CR do not affect line counting.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    symbols: list[dict] = []
    imports: list[dict] = []
    exports: list[dict] = []

    for m in FUNC_DECL_RE.finditer(text):
        line_start = text.rfind("\n", 0, m.start()) + 1
        line = text.count("\n", 0, m.start()) + 1
        column = m.start() - line_start + 1
        symbols.append(
            {
                "name": m.group(1),
                "kind": "function",
                "loc": {"line": line, "column": column},
            }
        )

    for m in IMPORT_RE.finditer(text):
        src = m.group(1) or m.group(2)
        if src:
            stmt = text[m.start(): m.end()]
            if stmt.strip().startswith("import type"):
                continue
            imports.append({"src": src, "symbols": []})

    for m in EXPORT_FUNC_RE.finditer(text):
        exports.append({"name": m.group(1), "kind": "function"})
    for m in EXPORT_DEFAULT_FUNC_RE.finditer(text):
        name = m.group(1) or "default"
        exports.append({"name": name, "kind": "function"})
    for m in EXPORT_CONST_RE.finditer(text):
        exports.append({"name": m.group(1), "kind": "var"})
    for m in EXPORT_LIST_RE.finditer(text):
        names = [part.strip() for part in m.group(1).split(",") if part.strip()]
        for n in names:
            exports.append({"name": n, "kind": "var"})
    for m in MODULE_EXPORTS_RE.finditer(text):
        names = [part.split(":")[0].strip() for part in m.group(1).split(",") if part.strip()]
        for n in names:
            exports.append({"name": n, "kind": "var"})

    return {"file": file_path, "symbols": symbols, "imports": imports, "exports": exports}
