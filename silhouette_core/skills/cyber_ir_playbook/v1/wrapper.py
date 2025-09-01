import json
from silhouette_core.skills.cyber_common import write_result


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

    plan = [
        "notify_executives",
        "coordinate_pr",
        "update_stakeholders",
    ]
    contacts = [
        "ir_lead",
        "legal",
        "pr",
        "it_ops",
    ]
    inject_library = {
        "ransomware": ["ransom_note", "encrypted_files"],
        "credential": ["phishing_email", "vpn_login"],
        "pii": ["lost_laptop", "db_dump"],
    }
    injects = inject_library.get(incident, ["generic_alert"])
    schedule = [
        {
            "minute": idx * 15,
            "inject": inj,
        }
        for idx, inj in enumerate(injects)
    ]
    drill = [
        {
            "team": team,
            "inject": inj,
        }
        for team, inj in zip(["red", "blue", "white"] * len(injects), injects)
    ]
    after_action = [
        "what_went_well",
        "what_to_improve",
        "follow_up_actions",
    ]
    from datetime import datetime, timezone
    playbook = {
        "schema": "ir_playbook.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "incident": incident,
        "steps": steps,
        "communication_plan": plan,
        "contacts": contacts,
        "injects": injects,
        "schedule": schedule,
        "drill": drill,
        "after_action": after_action,
    }
    path = write_result("ir_playbook", playbook, run_dir=out_dir)
    return json.dumps({"ok": True, "result": path})
