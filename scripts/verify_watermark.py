#!/usr/bin/env python
import argparse
import json
import pathlib
import sys


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact_dir", required=True)
    ap.add_argument("--require_license_tag", default="Silhouette-Proprietary")
    args = ap.parse_args()

    p = pathlib.Path(args.artifact_dir) / "WATERMARK.json"
    if not p.exists():
        print(f"Missing watermark: {p}", file=sys.stderr)
        sys.exit(2)
    wm = json.loads(p.read_text(encoding="utf-8"))
    if wm.get("license_tag") != args.require_license_tag:
        print(
            f"License tag mismatch: {wm.get('license_tag')} != {args.require_license_tag}",
            file=sys.stderr,
        )
        sys.exit(2)
    print("Watermark OK")


if __name__ == "__main__":
    main()
