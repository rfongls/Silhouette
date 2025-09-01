#!/usr/bin/env python
import re, sys, pathlib

ROOT = pathlib.Path('.').resolve()
EXTS = {'.py', '.md', '.yaml', '.yml'}

# Patterns → Replacements
REGISTRY_PATTERN = "skills" + "/registry.yaml"
RULES = [
    # Python imports
    (re.compile(r"\bfrom\s+skills\.", re.M), "from silhouette_core.skills."),
    # Registry path strings in docs/code
    (re.compile(REGISTRY_PATTERN, re.M), "silhouette_core/skills/registry.yaml"),
]

def should_edit(p: pathlib.Path) -> bool:
    return p.is_file() and p.suffix in EXTS and ("venv" not in p.parts) and (".git" not in p.parts) and ("__pycache__" not in p.parts)

def rewrite_file(p: pathlib.Path) -> int:
    txt = p.read_text(encoding='utf-8', errors='ignore')
    orig = txt
    for pat, rep in RULES:
        txt = pat.sub(rep, txt)
    if txt != orig:
        p.write_text(txt, encoding='utf-8')
        return 1
    return 0

def main():
    changed = 0
    for f in ROOT.rglob('*'):
        if should_edit(f):
            changed += rewrite_file(f)
    print(f"[refactor] files changed: {changed}")
    sys.exit(0)

if __name__ == '__main__':
    main()
