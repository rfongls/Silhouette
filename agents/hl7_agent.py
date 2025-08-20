from __future__ import annotations
from typing import Dict, Any
from skills.hl7_drafter import draft_message
from interfaces.hl7.mllp_client import send


class HL7Agent:
    async def draft_send(self, message_type: str, data: Dict[str, Any], host: str, port: int, tls: bool = False) -> Dict[str, str]:
        message = draft_message(message_type, data)
        ack = await send(host, port, message, tls=tls)
        return {"message": message, "ack": ack}
