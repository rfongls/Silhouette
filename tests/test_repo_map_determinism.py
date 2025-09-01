from __future__ import annotations
import json, hashlib
from pathlib import Path
from silhouette_core.repo_map import build_repo_map


def _h(obj) -> str:
    return hashlib.sha1(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def test_repo_map_is_deterministic(tmp_path: Path):
    (tmp_path/"pkg").mkdir()
    (tmp_path/"pkg"/"a.py").write_text("print('a')\n")
    (tmp_path/"pkg"/"b.ts").write_text("export const x=1;\n")
    files = ["pkg/a.py", "pkg/b.ts"]

    m1 = build_repo_map(tmp_path, files, compute_hashes=False)
    m2 = build_repo_map(tmp_path, files, compute_hashes=False)

    for k in ("version", "root", "detected_languages", "language_counts", "files", "stats"):
        assert k in m1 and k in m2

    assert _h(m1) == _h(m2)
