"""Simple file-based memory core placeholder."""

from pathlib import Path

LOG_DIR = Path("logs")
MEMORY_FILE = Path("memory.txt")


def ingest_logs():
    """Ingest log files into a single memory file."""
    with open(MEMORY_FILE, "a") as mem:
        for log in LOG_DIR.glob("*.txt"):
            with open(log, "r") as f:
                mem.write(f.read())


def query_memory(term: str) -> list[str]:
    """Return lines containing the term."""
    if not MEMORY_FILE.exists():
        return []
    results = []
    with open(MEMORY_FILE, "r") as mem:
        for line in mem:
            if term.lower() in line.lower():
                results.append(line.strip())

    return results
