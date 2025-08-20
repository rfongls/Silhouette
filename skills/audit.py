from typing import Dict, Any
import uuid
import datetime as dt

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
        "recorded": dt.datetime.utcnow().isoformat(),
        "outcome": 0 if outcome == "success" else 8,
        "agent": [{"who": {"display": who}}],
        "source": {"observer": {"display": "Silhouette Core"}},
        "entity": [{"what": {"display": what}}],
    }
