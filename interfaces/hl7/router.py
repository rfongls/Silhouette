from __future__ import annotations
import importlib, asyncio
from typing import Any, Dict
from skills.audit import fhir_audit_event, emit_and_persist


class HL7Router:
    def __init__(self, routes: Dict[str, Any]):
        self.routes = routes.get("routes", routes)

    async def process(self, message: str) -> str:
        lines = message.split("\r")
        msh = lines[0].split("|")
        msg_type = msh[8] if len(msh) > 8 else ""
        msg_id = msh[9] if len(msh) > 9 else ""
        handler_spec = self.routes.get(msg_type, {}).get("pipeline")
        status = "AA"
        outcome = "success"
        try:
            if handler_spec:
                mod_name, func_name = handler_spec.split(":")
                func = getattr(importlib.import_module(mod_name), func_name)
                res = func(message)
                if asyncio.iscoroutine(res):
                    await res
            else:
                raise ValueError("No route")
        except Exception:
            status = "AE"
            outcome = "error"
        emit_and_persist(fhir_audit_event("process", outcome, "HL7Router", msg_type))
        return self._ack(status, msg_id)

    @staticmethod
    def _ack(status: str, msg_id: str) -> str:
        return f"MSH|^~\\&|ROUTER|SILHOUETTE|||||ACK|{msg_id}|P|2.5.1\rMSA|{status}|{msg_id}\r"
