import multiprocessing as mp
import itertools
import shutil
import time
from pathlib import Path
from typing import Dict, List

from memory_merge import merge_memories

# Global registry of running agents
AGENTS: Dict[int, dict] = {}
_COUNTER = itertools.count(1)


def _agent_loop(agent_id: int, stop: mp.Event) -> None:
    """Simple agent process that keeps its own memory file."""
    mem_path = Path(f"memory_{agent_id}.jsonl")
    mem_path.touch(exist_ok=True)
    while not stop.is_set():
        time.sleep(0.1)


def spawn_agent(template: Path | None = None) -> int:
    """Start a new agent process.

    Returns the agent id.
    """
    agent_id = next(_COUNTER)
    stop = mp.Event()
    proc = mp.Process(target=_agent_loop, args=(agent_id, stop), daemon=True)
    proc.start()
    mem_path = Path(f"memory_{agent_id}.jsonl")
    if template and template.exists():
        shutil.copy(template, mem_path)
    AGENTS[agent_id] = {"process": proc, "stop": stop}
    return agent_id


def list_agents() -> List[int]:
    """Return list of active agent IDs."""
    return [aid for aid, info in AGENTS.items() if info["process"].is_alive()]


def shutdown_agent(agent_id: int) -> None:
    info = AGENTS.get(agent_id)
    if not info:
        return
    info["stop"].set()
    info["process"].join(timeout=1)
    AGENTS.pop(agent_id, None)


def fork_agent(agent_id: int) -> int:
    """Fork an agent by copying its memory into a new agent."""
    mem_src = Path(f"memory_{agent_id}.jsonl")
    new_id = spawn_agent(mem_src if mem_src.exists() else None)
    return new_id


def merge_agents(target_id: int, source_id: int) -> int:
    """Merge memory from source agent into target. Returns new line count."""
    target = Path(f"memory_{target_id}.jsonl")
    source = Path(f"memory_{source_id}.jsonl")
    return merge_memories(target, source)


def export_agent(agent_id: int, dest: Path) -> None:
    mem = Path(f"memory_{agent_id}.jsonl")
    if mem.exists():
        shutil.copy(mem, dest)


def import_agent(agent_id: int, src: Path) -> None:
    mem = Path(f"memory_{agent_id}.jsonl")
    if not src.exists():
        return
    text = src.read_text()
    with open(mem, "a", encoding="utf-8") as f:
        f.write(text)
