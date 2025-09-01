import json
from skills.cyber_common import write_result


def tool(payload: str) -> str:
    """Build a minimal incident response playbook for the given incident type.

    Input JSON: {"incident":"ransomware","out_dir":"..."}
    """
    args = json.loads(payload or "{}")
    incident = args.get("incident", "generic")
    out_dir = args.get("out_dir")
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
    path = write_result("ir_playbook", playbook, run_dir=out_dir)
    return json.dumps({"ok": True, "result": path})
