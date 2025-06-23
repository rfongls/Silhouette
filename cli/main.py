#!/usr/bin/env python3
"""
Silhouette Core CLI entrypoint.
Adds :replay, :selfcheck, and :backup commands.
"""

import argparse
import sys
from pathlib import Path

from export import export_state
from replay_log_to_memory import parse_session_logs
from selfcheck_engine import main as run_selfcheck

def repl():
    print("Silhouette Core CLI. Type :help for commands.")
    while True:
        try:
            cmd = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break
        if not cmd:
            continue
        if cmd == ":help":
            show_help()
        elif cmd == ":replay":
            parse_session_logs(Path("logs"), Path("memory.jsonl"))
        elif cmd == ":selfcheck":
            run_selfcheck()
        elif cmd == ":backup":
            export_state()
        elif cmd in (":exit", ":quit"):
            break
        else:
            print(f"Unknown command: {cmd}")

def show_help():
    print("Available commands:")
    print("  :help      Show this help message")
    print("  :replay    Replay session logs into memory.jsonl")
    print("  :selfcheck Verify system files and integrity")
    print("  :backup    Export full system state to archive")
    print("  :exit      Exit the CLI")

def main():
    parser = argparse.ArgumentParser(
        description="Silhouette Core CLI"
    )
    parser.add_argument(
        "--no-repl", action="store_true",
        help="Do not start interactive shell"
    )
    args = parser.parse_args()
    if args.no_repl:
        sys.exit(0)
    repl()

if __name__ == "__main__":
    main()
