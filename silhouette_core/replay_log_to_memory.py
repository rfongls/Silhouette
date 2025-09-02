#!/usr/bin/env python3
"""
replay_log_to_memory.py

Parses logs/session_*.txt and rebuilds memory.jsonl from session logs.
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path


def parse_session_logs(log_dir: Path, output_file: Path):
    """
    Read each session_*.txt in log_dir, extract user inputs, and write to memory.jsonl.
    """
    entries = []
    log_dir = log_dir.expanduser().resolve()
    if not log_dir.is_dir():
        logging.error("Log directory not found: %s", log_dir)
        sys.exit(1)
    log_files = sorted(log_dir.glob("session_*.txt"))
    if not log_files:
        logging.warning("No session log files found in %s", log_dir)
    for path in log_files:
        for line in path.read_text(encoding="utf-8").splitlines():
            match = re.match(r"\[.*?\]\s+USER:\s+(.*)", line)
            if match:
                entries.append({"role": "user", "content": match.group(1).strip()})
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as out:
        for entry in entries:
            out.write(json.dumps(entry, ensure_ascii=False) + "\n")
    logging.info("Replayed %d entries into %s", len(entries), output_file)
    return len(entries)

def main():
    parser = argparse.ArgumentParser(
        description="Replay session logs into memory.jsonl"
    )
    parser.add_argument(
        "--logs", type=Path, default=Path("logs"),
        help="Directory containing session_*.txt files"
    )
    parser.add_argument(
        "--output", type=Path, default=Path("memory.jsonl"),
        help="Output memory JSONL file"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parse_session_logs(args.logs, args.output)

if __name__ == "__main__":
    main()
