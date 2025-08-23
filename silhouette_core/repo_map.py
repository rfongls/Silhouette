from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable, Dict, List

LANG_MAP = {
    ".py": "py",
    ".ts": "ts",
    ".tsx": "ts",
    ".js": "js",
    ".jsx": "js",
    ".go": "go",
    ".java": "java",
    ".cs": "cs",
}


def _lang_for_path(path: Path) -> str | None:
    return LANG_MAP.get(path.suffix.lower())


def build_repo_map(root: Path, files: Iterable[str], compute_hashes: bool = False) -> Dict:
    root = root.resolve()
    detected = []
    language_counts: Dict[str, int] = {}
    file_entries: List[Dict[str, object]] = []
    code_file_count = 0
    for rel in files:
        p = root / rel
        if not p.is_file():
            continue
        size = p.stat().st_size
        entry: Dict[str, object] = {"path": rel, "size": size}
        lang = _lang_for_path(p)
        if lang:
            detected.append(lang)
            language_counts[lang] = language_counts.get(lang, 0) + 1
            code_file_count += 1
        if compute_hashes and size <= 5 * 1024 * 1024:
            sha1 = hashlib.sha1(p.read_bytes()).hexdigest()
            entry["hash"] = f"sha1:{sha1}"
        file_entries.append(entry)
    data = {
        "version": "0.2.0",
        "root": str(root),
        "detected_languages": sorted(set(detected)),
        "language_counts": language_counts,
        "files": file_entries,
        "stats": {
            "file_count": len(file_entries),
            "code_file_count": code_file_count,
        },
    }
    return data


def save_repo_map(data: Dict, outpath: Path) -> None:
    outpath.parent.mkdir(parents=True, exist_ok=True)
    outpath.write_text(json.dumps(data, indent=2))
