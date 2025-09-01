import json
from skills.cyber_common import write_result


def tool(payload: str) -> str:
    """Build a minimal incident response playbook for the given incident type.

    Input JSON: {"incident":"ransomware","out_dir":"..."}
    """
    args = json.loads(payload or "{}")
    incident = args.get("incident", "generic")
    out_dir = args.get("out_dir")
    templates = {
        "ransomware": [
            "identify",
            "isolate_systems",
            "notify_ir_team",
            "restore_from_backups",
            "lessons_learned",
        ],
        "credential": [
            "identify_compromise",
            "reset_credentials",
            "notify_users",
            "monitor_abuse",
            "lessons_learned",
        ],
        "pii": [
            "identify_exposure",
            "contain_data",
            "notify_privacy_officer",
            "notify_affected_users",
            "lessons_learned",
        ],
    }

    steps = templates.get(incident, [
        "identify",
        "contain",
        "eradicate",
        "recover",
        "lessons_learned",
    ])

    playbook = {"incident": incident, "steps": steps}
    path = write_result("ir_playbook", playbook, run_dir=out_dir)
    return json.dumps({"ok": True, "result": path})
