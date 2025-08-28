"""Compatibility shim: routes legacy imports to the current agent loop.
Keep until all docs/examples are updated to `agent_loop.py`.
"""

from .agent_loop import Agent


def run_agent_loop(message: str) -> str:
    """Minimal wrapper around :class:`Agent`."""
    agent = Agent()
    return agent.loop(message)


__all__ = ["run_agent_loop", "Agent"]
