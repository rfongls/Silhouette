from fastapi.testclient import TestClient
from server import app

client = TestClient(app)

def test_validate_accepts_form():
    r = client.post(
        "/api/interop/validate",
        data={"text": "MSH|^~\\&|A|B|C|D|202001011230||ADT^A01|1|P|2.4"},
        headers={"Accept": "application/json"},
    )
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


def test_deidentify_accepts_form():
    r = client.post(
        "/api/interop/deidentify",
        data={"text": "PID|1||12345^^^HOSP^MR|..."},
        headers={"Accept": "application/json"},
    )
    assert r.status_code == 200
    j = r.json()
    assert "text" in j


def test_deidentify_plaintext_via_format_override():
    r = client.post(
        "/api/interop/deidentify?format=txt",
        data={"text": "PID|1||12345^^^HOSP^MR|..."},
        headers={"Accept": "application/json"},
    )
    assert r.status_code == 200
    assert r.text.startswith("PID|")
    assert r.headers.get("content-type", "").lower().startswith("text/plain")


def test_mllp_send_rejects_cleanly_without_host_port():
    r = client.post(
        "/api/interop/mllp/send",
        data={"messages": "MSH|^~\\&|..."},
        headers={"Accept": "application/json"},
    )
    assert r.status_code in (400, 404)
