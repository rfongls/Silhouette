#!/usr/bin/env python
import re, sys, pathlib
ROOT = pathlib.Path('.').resolve()
EXTS = {'.py', '.md', '.yaml', '.yml'}
RULES = [
    (re.compile(r"\bfrom\s+skills\.", re.M), "from silhouette_core.skills."),
    (re.compile(r"skills/registry\.yaml", re.M), "silhouette_core/skills/registry.yaml"),
]
def should_edit(p): return p.is_file() and p.suffix in EXTS and ".git" not in p.parts and "__pycache__" not in p.parts and "venv" not in p.parts
def rewrite(p):
    t = p.read_text(encoding='utf-8', errors='ignore'); o = t
    for pat, rep in RULES: t = pat.sub(rep, t)
    if t != o: p.write_text(t, encoding='utf-8'); return 1
    return 0
print(f"[refactor] files changed: {sum(rewrite(p) for p in ROOT.rglob('*') if should_edit(p))}")
