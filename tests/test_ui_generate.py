import pytest
pytest.importorskip("fastapi")
pytest.importorskip("multipart")

from fastapi.testclient import TestClient  # noqa: E402
from server import app  # noqa: E402
from api import debug_log  # noqa: E402

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


def test_ui_generate_records_debug_events(monkeypatch, tmp_path):
    monkeypatch.setattr(debug_log, "LOG_FILE", tmp_path / "generator_debug.log")
    debug_log.reset_debug_log(clear_file=True)
    debug_log.set_debug_enabled(True)
    debug_log.reset_debug_log(clear_file=True)

    resp = client.post(
        "/ui/interop/generate",
        data={"version": "hl7-v2-4", "trigger": "ADT_A03", "count": "1"},
        headers={"Accept": "text/plain", "HX-Request": "true"},
    )
    assert resp.status_code == 200

    lines = debug_log.tail_debug_lines(20)
    joined = "\n".join(lines)
    assert "ui.generate.invoke" in joined
    assert "ui.generate.body" in joined
    assert "ui.generate.result" in joined
