"""Stub for agent-to-agent messaging."""

from typing import Dict, Any


def send_message(address: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Send a message to another agent.

    Networking is not implemented in this offline stub.
    """
    raise NotImplementedError("Messaging layer requires network support")
