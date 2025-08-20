import json
from connectors.hie.mock_hie_connector import MockHIEConnector
from connectors.tefca.mock_tefca_connector import MockTEFCAConnector
from skills.audit import AUDIT_FILE
import pathlib


def test_hie_emits_audit_event(tmp_path, monkeypatch):
    audit_file = tmp_path / "audit.ndjson"
    monkeypatch.setattr("skills.audit.AUDIT_FILE", audit_file)

    c = MockHIEConnector()
    docs = c.query_documents("123456")
    assert isinstance(docs, list) and len(docs) >= 1

    text = audit_file.read_text(encoding="utf-8")
    lines = [json.loads(l) for l in text.strip().splitlines() if l.strip()]
    assert any(ev.get("resourceType") == "AuditEvent" for ev in lines)
    assert any("RLS query" in ev["entity"][0]["what"]["display"] for ev in lines)


def test_tefca_emits_audit_event(tmp_path, monkeypatch):
    audit_file = tmp_path / "audit_tefca.ndjson"
    monkeypatch.setattr("skills.audit.AUDIT_FILE", audit_file)

    t = MockTEFCAConnector()
    res = t.cross_qhin_query({"family_name": "DOE", "dob": "1980-01-01"})
    assert "MOCK-QHIN" in res.get("qhin", "")

    text = audit_file.read_text(encoding="utf-8")
    lines = [json.loads(l) for l in text.strip().splitlines() if l.strip()]
    assert any(ev.get("resourceType") == "AuditEvent" for ev in lines)
    assert any("Cross-QHIN query" in ev["entity"][0]["what"]["display"] for ev in lines)
