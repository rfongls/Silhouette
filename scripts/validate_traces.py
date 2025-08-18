#!/usr/bin/env python
import argparse
import json
import pathlib
import sys

REQ = {"task_id","suite","timestamp","instruction","input","files","commands","stdout","teacher_output"}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="JSONL file of traces")
    args = ap.parse_args()
    p = pathlib.Path(args.path)
    if not p.exists():
        print(f"Not found: {p}", file=sys.stderr)
        sys.exit(2)
    n = 0
    with p.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except Exception as e:
                print(f"Line {i}: invalid JSON: {e}", file=sys.stderr)
                sys.exit(2)
            miss = REQ - obj.keys()
            if miss:
                print(f"Line {i}: missing {miss}", file=sys.stderr)
                sys.exit(2)
            if not isinstance(obj["files"], list):
                print(f"Line {i}: files must be list", file=sys.stderr)
                sys.exit(2)
            n += 1
    print(f"OK: {n} traces")

if __name__ == "__main__":
    main()
