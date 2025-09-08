from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import interop_gen as ig

app = FastAPI()
app.include_router(ig.router)
client = TestClient(app)


def test_generate_single_from_template():
    body = {
        "version": "hl7-v2-4",
        "template_relpath": "hl7-v2-4/ADT_A01.hl7",
        "count": 3,
        "seed": 123,
        "ensure_unique": True,
        "include_clinical": True,
        "deidentify": True,
    }
    r = client.post("/api/interop/generate", json=body)
    assert r.status_code == 200
    raw = r.text.strip()
    parts = raw.split("\nMSH")
    msgs = [parts[0]] + ["MSH" + p for p in parts[1:]] if parts else []
    assert len(msgs) == 3
    ids = set()
    for msg in msgs:
        msh = next(l for l in msg.splitlines() if l.startswith("MSH|"))
        mcid = msh.split("|")[9]
        ids.add(mcid)
    assert len(ids) == 3


def test_generate_from_trigger_any_extension(tmp_path, monkeypatch):
    base = tmp_path / "templates" / "hl7" / "hl7-v2-4"
    base.mkdir(parents=True)
    (base / "ZZZ_TEST.hl7.j2").write_text(
        "MSH|^~\\&||||||ZZZ_TEST|MSGID|P|2.4\\r",
        encoding="utf-8",
    )
    monkeypatch.setattr(ig, "TEMPLATES_HL7_DIR", tmp_path / "templates" / "hl7")
    app = FastAPI()
    app.include_router(ig.router)
    local_client = TestClient(app)
    r = local_client.post(
        "/api/interop/generate",
        json={"version": "hl7-v2-4", "trigger": "ZZZ_TEST"},
    )
    assert r.status_code == 200
    assert "ZZZ_TEST" in r.text


def test_auto_deidentify_when_count_gt_one():
    body = {
        "version": "hl7-v2-4",
        "template_relpath": "hl7-v2-4/ADT_A01.hl7",
        "count": 2,
    }
    r = client.post("/api/interop/generate", json=body)
    assert r.status_code == 200
    assert "Davis^Jessica" not in r.text


def test_deidentify_can_be_disabled():
    body = {
        "version": "hl7-v2-4",
        "template_relpath": "hl7-v2-4/ADT_A01.hl7",
        "count": 2,
        "deidentify": False,
    }
    r = client.post("/api/interop/generate", json=body)
    assert r.status_code == 200
    assert "Davis^Jessica" in r.text

def test_generate_accepts_form_posts():
    """HTMX-style form posts should be accepted without JSON payloads."""
    data = {
        "version": "hl7-v2-4",
        "trigger": "ADT_A01",
        "count": "1",
    }
    r = client.post("/api/interop/generate", data=data)
    assert r.status_code == 200
    # The returned message should contain the ADT^A01 event in the MSH segment
    assert "ADT^A01" in r.text

