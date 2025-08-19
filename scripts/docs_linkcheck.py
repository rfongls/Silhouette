#!/usr/bin/env python3
"""Check local markdown links for validity."""
import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
missing = []
for md in ROOT.rglob("*.md"):
    text = md.read_text(encoding="utf-8", errors="ignore")
    links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
    for link in links:
        if link.startswith("http://") or link.startswith("https://") or link.startswith("mailto:"):
            continue
        target = (md.parent / link.split('#')[0]).resolve()
        if not target.exists():
            missing.append(f"{md}: {link}")
if missing:
    for m in missing:
        print(m)
    sys.exit(1)
