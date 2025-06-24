from pathlib import Path
from typing import Iterable


def _read_lines(path: Path) -> Iterable[str]:
    if not path.exists():
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return [line.rstrip('\n') for line in f]


def merge_memories(target: Path, source: Path) -> int:
    """Merge unique lines from source into target. Returns number of added lines."""
    target_lines = set(_read_lines(target))
    source_lines = _read_lines(source)
    new_lines = [line for line in source_lines if line not in target_lines]
    if new_lines:
        with open(target, 'a', encoding='utf-8') as f:
            for line in new_lines:
                f.write(line + '\n')
    return len(new_lines)
