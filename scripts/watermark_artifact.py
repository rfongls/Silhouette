#!/usr/bin/env python
import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import time

def git_rev():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    except Exception:
        return None

def sha256_dir(path: pathlib.Path, max_bytes: int = 5_000_000) -> str:
    h = hashlib.sha256()
    for p in sorted(path.rglob("*")):
        if p.is_file() and p.stat().st_size <= max_bytes:
            h.update(p.read_bytes())
    return h.hexdigest()

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact_dir", required=True, help="Directory containing model/artifact")
    ap.add_argument("--customer_id", default="")
    ap.add_argument("--license_tag", default="Silhouette-Proprietary")
    ap.add_argument("--notes", default="")
    args = ap.parse_args()

    out_dir = pathlib.Path(args.artifact_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    wm = {
        "created_at_utc": int(time.time()),
        "git_commit": git_rev(),
        "artifact_dir": str(out_dir),
        "artifact_sha256": sha256_dir(out_dir),
        "license_tag": args.license_tag,
        "customer_id": args.customer_id or None,
        "notes": args.notes or None,
        "provenance": {
            "tool": "scripts/watermark_artifact.py",
            "user": os.environ.get("GITHUB_ACTOR") or os.environ.get("USER") or None,
            "ci_run_id": os.environ.get("GITHUB_RUN_ID"),
        },
    }
    (out_dir / "WATERMARK.json").write_text(json.dumps(wm, indent=2), encoding="utf-8")

    cfg = out_dir / "config.json"
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            data["_silhouette_watermark"] = {
                "path": "WATERMARK.json",
                "license_tag": args.license_tag,
            }
            cfg.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    print(f"Wrote watermark to {out_dir/'WATERMARK.json'}")

if __name__ == "__main__":
    main()
