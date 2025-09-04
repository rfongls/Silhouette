import json
from pathlib import Path
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_admin_seeds_validation_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    r = client.post(
        "/admin/seeds/save",
        data={
            "cve_json": "{ not-json }",
            "kev_json": "{}",
            "scope_text": "in-scope: example.com",
        },
    )
    assert r.status_code == 400
    assert "application/json" in r.headers.get("content-type", "")
    assert "Invalid" in r.text or "Expecting" in r.text


def test_admin_seeds_happy_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    r = client.post(
        "/admin/seeds/save",
        data={
            "cve_json": json.dumps({"cve": []}),
            "kev_json": json.dumps({"kev": []}),
            "scope_text": "in-scope: example.com",
        },
    )
    assert r.status_code == 200
    assert Path("data/security/seeds/cve/cve_seed.json").exists()
    assert Path("data/security/seeds/kev/kev_seed.json").exists()
    assert Path("docs/cyber/scope_example.txt").exists()


def test_interop_hl7_pretty_error():
    r = client.post(
        "/interop/hl7/draft-send",
        data={"message_type": "ADT_A01", "json_data": "{ bad", "host": "127.0.0.1", "port": 2575},
    )
    assert r.status_code == 200
    assert '"ok": false' in r.text.lower()
