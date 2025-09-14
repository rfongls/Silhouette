import pytest
pytest.importorskip("fastapi")
pytest.importorskip("multipart")

from fastapi.testclient import TestClient  # noqa: E402
from server import app  # noqa: E402

client = TestClient(app)

def test_api_generate_form_post_works():
    r = client.post(
        "/api/interop/generate",
        data={"version": "hl7-v2-4", "trigger": "ADT_A03", "count": "1"},
        headers={"Accept": "text/plain"},
    )
    assert r.status_code == 200
    assert r.text.startswith("MSH|")


def test_ui_generate_htmx_plaintext_works():
    r = client.post(
        "/ui/interop/generate",
        data={"version": "hl7-v2-4", "trigger": "ADT_A03", "count": "1"},
        headers={"Accept": "text/plain", "HX-Request": "true"},
    )
    assert r.status_code == 200
    assert r.text.startswith("MSH|")

def test_ui_generate_html_fallback_works():
    r = client.post(
        "/ui/interop/generate",
        data={"version": "hl7-v2-4", "trigger": "ADT_A03", "count": "1"},
    )
    assert r.status_code == 200
    assert "MSH|" in r.text
    assert "<pre" in r.text
