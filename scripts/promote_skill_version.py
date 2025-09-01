#!/usr/bin/env python
"""
Promote a skill to a new version:
- Copies silhouette_core/skills/<name>/<old_version>/ to silhouette_core/skills/<name>/<new_version>/
- Updates silhouette_core/skills/<name>/__init__.py to re-export new_version
- Updates silhouette_core/skills/registry.yaml to set version: <new_version> for that skill
"""
import argparse
import pathlib
import shutil
import sys
import yaml

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="skill name, e.g., http_get_json")
    ap.add_argument("--from_version", required=True, help="e.g., v1")
    ap.add_argument("--to_version", required=True, help="e.g., v2")
    args = ap.parse_args()

    skill_dir = pathlib.Path("silhouette_core/skills") / args.name
    src = skill_dir / args.from_version
    dst = skill_dir / args.to_version
    if not src.exists():
        print(f"Source version not found: {src}", file=sys.stderr)
        sys.exit(2)
    if dst.exists():
        print(f"Destination version already exists: {dst}", file=sys.stderr)
        sys.exit(2)

    shutil.copytree(src, dst)

    initp = skill_dir / "__init__.py"
    initp.write_text(f"from .{args.to_version}.wrapper import tool\n", encoding="utf-8")

    regp = pathlib.Path("silhouette_core/skills/registry.yaml")
    reg = {"skills": []}
    if regp.exists():
        reg = yaml.safe_load(regp.read_text(encoding="utf-8")) or {"skills": []}
    for s in reg["skills"]:
        if s.get("name") == args.name:
            s["version"] = args.to_version
            break
    regp.write_text(yaml.safe_dump(reg, sort_keys=False), encoding="utf-8")

    print(f"Promoted {args.name} from {args.from_version} to {args.to_version}")

if __name__ == "__main__":
    main()
