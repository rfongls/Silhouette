import json
from silhouette_core.pipelines import hl7_to_fhir
import skills.audit as audit

def test_deidentify_and_audit(tmp_path, monkeypatch):
    # redirect audit file
    audit_file = tmp_path / "audit.ndjson"
    monkeypatch.setattr(audit, "AUDIT_FILE", audit_file)

    hl7_to_fhir.translate(
        input_path="tests/data/hl7/adt_a01.hl7",
        map_path="maps/adt_uscore.yaml",
        out=str(tmp_path),
        bundle="transaction",
        server=None,
        token=None,
        validate=False,
        dry_run=True,
        message_mode=False,
        partner=None,
        message_endpoint=None,
        notify_url=None,
        deidentify=True,
    )

    patient_file = tmp_path / "fhir" / "ndjson" / "Patient.ndjson"
    line = patient_file.read_text().strip()
    patient = json.loads(line)
    assert "name" not in patient

    events = [json.loads(l) for l in audit_file.read_text().splitlines() if l.strip()]
    assert any(ev.get("resourceType") == "AuditEvent" for ev in events)
