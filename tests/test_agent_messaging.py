import pytest
from agent_messaging import send_message


def test_send_message_stub():
    with pytest.raises(NotImplementedError):
        send_message("localhost:8000", {"type": "ping"})
