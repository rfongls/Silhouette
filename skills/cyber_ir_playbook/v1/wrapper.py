import json
from skills.cyber_common import write_result


def tool(payload: str) -> str:
    """Build a minimal incident response playbook for the given incident type.

    Input JSON: {"incident": "ransomware"}
    """
    args = json.loads(payload or "{}")
    incident = args.get("incident", "generic")
    playbook = {
        "incident": incident,
        "steps": [
            "identify",
            "contain",
            "eradicate",
            "recover",
            "lessons_learned",
        ],
    }
    path = write_result("ir_playbook", playbook)
    return json.dumps({"ok": True, "result": path})
