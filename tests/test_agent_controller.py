from pathlib import Path
import time

from agent_controller import (
    spawn_agent,
    shutdown_agent,
    fork_agent,
    merge_agents,
    list_agents,
)


def test_spawn_and_shutdown():
    aid = spawn_agent()
    assert aid in list_agents()
    shutdown_agent(aid)
    time.sleep(0.1)
    assert aid not in list_agents()


def test_fork_and_merge(tmp_path):
    a = spawn_agent()
    mem_a = Path(f"memory_{a}.jsonl")
    mem_a.write_text("hello\n")
    b = fork_agent(a)
    mem_b = Path(f"memory_{b}.jsonl")
    with open(mem_b, "a") as f:
        f.write("world\n")
    count = merge_agents(a, b)
    shutdown_agent(a)
    shutdown_agent(b)
    text = mem_a.read_text()
    assert count == 1
    assert "world" in text
    mem_a.unlink()
    mem_b.unlink()
