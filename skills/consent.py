from typing import Dict, Any
import uuid
import datetime as dt
import yaml
import pathlib

def build_fhir_consent(patient_id: str, template_path: str) -> Dict[str, Any]:
    data = yaml.safe_load(pathlib.Path(template_path).read_text(encoding="utf-8"))
    now = dt.datetime.now(dt.UTC).date().isoformat()
    return {
        "resourceType": "Consent",
        "id": str(uuid.uuid4()),
        "status": data.get("status", "active"),
        "scope": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/consentscope",
                    "code": "patient-privacy",
                }
            ]
        },
        "patient": {"reference": f"Patient/{patient_id}"},
        "dateTime": now,
        "policy": [{"authority": "TEFCA", "uri": data.get("policy_id", "TEFCA-DEFAULT")}],
        "provision": {"type": "permit"},
    }
