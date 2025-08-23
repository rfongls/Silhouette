from fastapi.testclient import TestClient
from server import app


def test_ui_page_renders():
    client = TestClient(app)
    r = client.get("/ui/hl7")
    assert r.status_code == 200
    assert "HL7 Draft & Send" in r.text
