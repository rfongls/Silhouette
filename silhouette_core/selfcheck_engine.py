#!/usr/bin/env python3
"""
selfcheck_engine.py

Validates presence and integrity of persona.dsl and memory.jsonl, reporting issues.
"""

import argparse
import json
import sys
from pathlib import Path

from .persona_audit import audit_memory
from .drift_detector import main as drift_main
from .session_summarizer import main as summary_main

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

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Run self-checks on system state"
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit with error if warnings are found"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run extended monitoring checks",
    )
    args = parser.parse_args(argv)
    missing = check_files()
    errors = check_memory(Path("memory.jsonl"))
    violations = audit_memory(Path("memory.jsonl"), Path("persona.dsl"))
    if args.full:
        drift_main([])
        summary_main([])
    if missing or errors or violations:
        if violations:
            print("Persona violations detected:")
            for v in violations:
                print("  ", v)
        if args.strict:
            sys.exit(1)
        else:
            print("Self-check completed with issues.")
    else:
        print("All checks passed. Files are present and valid.")

if __name__ == "__main__":
    main()
