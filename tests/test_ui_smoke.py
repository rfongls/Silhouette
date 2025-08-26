import pytest
pytest.importorskip("fastapi")
pytest.importorskip("multipart")

from fastapi.testclient import TestClient  # noqa: E402
from server import app  # noqa: E402


def test_ui_page_renders():
    client = TestClient(app)
    r = client.get("/ui/hl7")
    assert r.status_code == 200
    assert "HL7 Draft & Send" in r.text
