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
        "output_format": "ndjson",
    }
    r = client.post("/api/interop/generate", json=body)
    assert r.status_code == 200
    lines = r.text.strip().splitlines()
    assert len(lines) == 3
    ids = set()
    import json as _json

    for line in lines:
        obj = _json.loads(line)
        hl7 = obj["hl7"]
        msh = next(l for l in hl7.splitlines() if l.startswith("MSH|"))
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
