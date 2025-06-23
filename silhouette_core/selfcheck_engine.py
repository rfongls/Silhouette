#!/usr/bin/env python3
"""
selfcheck_engine.py

Validates presence and integrity of persona.dsl and memory.jsonl, reporting issues.
"""

import argparse
import json
import sys
from pathlib import Path

REQUIRED_FILES = ["persona.dsl", "memory.jsonl"]

def check_files():
    missing = [f for f in REQUIRED_FILES if not Path(f).is_file()]
    if missing:
        print("Missing required files:", ", ".join(missing))
    return missing

def check_memory(path: Path):
    errors = []
    if not path.is_file():
        return errors
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"Line {i}: {e}")
    if errors:
        print("Errors parsing memory.jsonl:")
        for err in errors:
            print("  ", err)
    return errors

def main():
    parser = argparse.ArgumentParser(
        description="Run self-checks on system state"
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit with error if warnings are found"
    )
    args = parser.parse_args()
    missing = check_files()
    errors = check_memory(Path("memory.jsonl"))
    if missing or errors:
        if args.strict:
            sys.exit(1)
        else:
            print("Self-check completed with issues.")
    else:
        print("All checks passed. Files are present and valid.")

if __name__ == "__main__":
    main()
