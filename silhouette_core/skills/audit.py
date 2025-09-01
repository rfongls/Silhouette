from typing import Dict, Any
import uuid
import datetime as dt
import pathlib
import json
import os

REPORTS_DIR = pathlib.Path("reports")
REPORTS_DIR.mkdir(exist_ok=True, parents=True)
AUDIT_FILE = REPORTS_DIR / "audit_events.ndjson"
MAX_LINES = int(os.getenv("AUDIT_MAX_LINES", "1000"))


def fhir_audit_event(action: str, outcome: str, who: str, what: str) -> Dict[str, Any]:
    return {
        "resourceType": "AuditEvent",
        "id": str(uuid.uuid4()),
        "type": {
            "system": "http://terminology.hl7.org/CodeSystem/audit-event-type",
            "code": "rest",
        },
        "subtype": [
            {
                "system": "http://hl7.org/fhir/restful-interaction",
                "code": action,
            }
        ],
        "action": action[:1].upper(),
        "recorded": dt.datetime.now(dt.UTC).isoformat(),
        "outcome": 0 if outcome == "success" else 8,
        "agent": [{"who": {"display": who}}],
        "source": {"observer": {"display": "Silhouette Core"}},
        "entity": [{"what": {"display": what}}],
    }


def emit_and_persist(event: Dict[str, Any]) -> None:
    with open(AUDIT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")
    _prune()


def _prune() -> None:
    try:
        lines = AUDIT_FILE.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return
    if len(lines) > MAX_LINES:
        AUDIT_FILE.write_text("\n".join(lines[-MAX_LINES:]) + "\n", encoding="utf-8")
