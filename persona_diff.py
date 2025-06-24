from pathlib import Path
from typing import List


def persona_path(agent_id: int) -> Path:
    return Path(f"persona_{agent_id}.dsl")


def diff_personas(agent_a: int, agent_b: int) -> List[str]:
    """Return line-based diff of two persona DSL files."""
    path_a = persona_path(agent_a)
    path_b = persona_path(agent_b)
    lines_a = set(path_a.read_text().splitlines()) if path_a.exists() else set()
    lines_b = set(path_b.read_text().splitlines()) if path_b.exists() else set()
    diff = []
    for line in sorted(lines_a - lines_b):
        diff.append(f"- {line}")
    for line in sorted(lines_b - lines_a):
        diff.append(f"+ {line}")
    return diff


def diff_with_base(agent_id: int, base: Path = Path("persona.dsl")) -> List[str]:
    path_a = persona_path(agent_id)
    lines_a = set(path_a.read_text().splitlines()) if path_a.exists() else set()
    lines_b = set(base.read_text().splitlines()) if base.exists() else set()
    diff = []
    for line in sorted(lines_a - lines_b):
        diff.append(f"- {line}")
    for line in sorted(lines_b - lines_a):
        diff.append(f"+ {line}")
    return diff
