import asyncio, yaml, json, pytest
from pathlib import Path
from interfaces.hl7.router import HL7Router

BAD = "MSH|^~\\&|IMM|SENDER|IIS|STATE|202402091030||VXU^V04|BAD1|P|2.5.1\rRXA|0|1\r"


@pytest.mark.hl7
def test_audit_records_error(tmp_path, monkeypatch):
    audit_file = tmp_path / "audit.ndjson"
    monkeypatch.setattr("skills.audit.AUDIT_FILE", audit_file)
    router = HL7Router(yaml.safe_load(open("config/routes.yaml")))
    ack = asyncio.run(router.process(BAD))
    assert "|AE|BAD1" in ack or "|AR|BAD1" in ack
    lines = [json.loads(x) for x in audit_file.read_text().splitlines() if x.strip()]
    assert any(e.get("resourceType") == "AuditEvent" and e.get("outcome", 1) != 0 for e in lines)
