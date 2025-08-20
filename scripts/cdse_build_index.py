#!/usr/bin/env python3
import json, pathlib, re

ROOT = pathlib.Path("docs/cyber/cdse")
OUT  = ROOT / "toolkit_index.json"

def split_sections(text):
    sections=[]; cur={"title":"Intro","body":""}
    for line in text.splitlines():
        if re.match(r"^#{1,3}\s+", line):
            if cur["body"].strip(): sections.append(cur)
            cur={"title":line.lstrip("# ").strip(), "body":""}
        else:
            cur["body"] += line+"\n"
    if cur["body"].strip(): sections.append(cur)
    return sections

def build():
    entries=[]
    for md in sorted(ROOT.glob("*.md")):
        doc_id = md.name
        text = md.read_text(encoding="utf-8")
        for i,sec in enumerate(split_sections(text), start=1):
            entries.append({
                "doc_id": doc_id,
                "section_id": f"s{i}",
                "title": sec["title"],
                "text": sec["body"].strip()
            })
    OUT.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} with {len(entries)} sections.")

if __name__=="__main__":
    build()
