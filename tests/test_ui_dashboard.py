import pytest

pytest.importorskip("fastapi")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server import app
from api import activity_log, debug_log, diag as diag_module
from api.http_logging import install_http_logging


client = TestClient(app)


def _prime_debug_log(monkeypatch, tmp_path):
    monkeypatch.setattr(debug_log, "LOG_FILE", tmp_path / "generator_debug.log")
    debug_log.reset_debug_log(clear_file=True)
    debug_log.set_debug_enabled(True)
    debug_log.reset_debug_log(clear_file=True)


def _prime_activity_log(monkeypatch, tmp_path):
    log_dir = tmp_path / "activity"
    log_path = log_dir / "activity.log"
    log_dir.mkdir(parents=True, exist_ok=True)
    activity_log._buffer.clear()  # type: ignore[attr-defined]
    monkeypatch.setattr(activity_log, "LOG_DIR", log_dir, raising=False)
    monkeypatch.setattr(activity_log, "ACTIVITY_FILE", log_path, raising=False)
    monkeypatch.setattr(diag_module, "ACTIVITY_FILE", log_path, raising=False)
    if log_path.exists():
        log_path.unlink()


def test_interop_dashboard_renders():
    response = client.get("/ui/interop/dashboard")
    assert response.status_code == 200
    assert "Generate Messages" in response.text


def test_diag_routes_available():
    response = client.get("/api/diag/routes")
    assert response.status_code == 200
    data = response.json()
    assert any(route["path"] == "/api/interop/generate" for route in data.get("routes", []))


def test_diag_logs_returns_recent_lines(monkeypatch, tmp_path):
    _prime_debug_log(monkeypatch, tmp_path)
    debug_log.record_debug_line("test event")
    response = client.get("/api/diag/logs")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 1
    assert any("test event" in line for line in payload["lines"])
    assert payload["enabled"] is True


def test_diag_logs_text_format(monkeypatch, tmp_path):
    _prime_debug_log(monkeypatch, tmp_path)
    debug_log.record_debug_line("plain view event")
    response = client.get("/api/diag/logs", params={"format": "text"})
    assert response.status_code == 200
    assert "plain view event" in response.text


def test_ui_logs_content_fragment(monkeypatch, tmp_path):
    _prime_debug_log(monkeypatch, tmp_path)
    debug_log.record_debug_line("ui fragment event")
    response = client.get("/ui/interop/logs/content")
    assert response.status_code == 200
    assert "ui fragment event" in response.text


def test_diag_debug_state_toggle(monkeypatch, tmp_path):
    _prime_debug_log(monkeypatch, tmp_path)
    resp = client.post("/api/diag/debug/state/disable")
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False
    assert debug_log.is_debug_enabled() is False
    resp = client.post("/api/diag/debug/state/enable")
    assert resp.status_code == 200
    assert resp.json()["enabled"] is True
    assert debug_log.is_debug_enabled() is True


def test_diag_debug_state_html_chip(monkeypatch, tmp_path):
    _prime_debug_log(monkeypatch, tmp_path)
    debug_log.set_debug_enabled(True)
    resp = client.get("/api/diag/debug/state", params={"format": "html"})
    assert resp.status_code == 200
    assert "Debug ON" in resp.text
    assert "debug-state-badge" in resp.text
    debug_log.set_debug_enabled(False)
    resp = client.get("/api/diag/debug/state", params={"format": "html"})
    assert resp.status_code == 200
    assert "Debug OFF" in resp.text
    assert "debug-state-badge" in resp.text
    debug_log.set_debug_enabled(True)


def test_diag_debug_state_toggle_returns_html_when_requested(monkeypatch, tmp_path):
    _prime_debug_log(monkeypatch, tmp_path)
    resp = client.post(
        "/api/diag/debug/state/disable",
        headers={"Accept": "text/html"},
    )
    assert resp.status_code == 200
    assert "debug-state-badge" in resp.text
    assert "Debug OFF" in resp.text
    resp = client.post(
        "/api/diag/debug/state/enable",
        headers={"Accept": "text/html"},
    )
    assert resp.status_code == 200
    assert "debug-state-badge" in resp.text
    assert "Debug ON" in resp.text


def test_debug_toggle_snippet_endpoint(monkeypatch, tmp_path):
    _prime_debug_log(monkeypatch, tmp_path)
    debug_log.set_debug_enabled(True)
    resp = client.get("/api/diag/debug/state/snippet", headers={"Accept": "text/html"})
    assert resp.status_code == 200
    assert "interop-debug-log" in resp.text
    assert "Debug ON" in resp.text


def test_diag_debug_event_endpoint(monkeypatch, tmp_path):
    _prime_debug_log(monkeypatch, tmp_path)
    resp = client.post("/api/diag/debug/event", json={"event": "ui-test", "detail": "clicked"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    payload = client.get("/api/diag/logs").json()
    assert any("ui.ui-test" in line for line in payload["lines"])
    client.post("/api/diag/debug/state/disable")
    resp = client.post("/api/diag/debug/event", json={"event": "ui-disabled"})
    assert resp.json()["enabled"] is False
    payload = client.get("/api/diag/logs").json()
    assert not any("ui.ui-disabled" in line for line in payload["lines"])
    debug_log.set_debug_enabled(True)


def test_ui_home_debug_panel(monkeypatch, tmp_path):
    _prime_debug_log(monkeypatch, tmp_path)
    debug_log.record_debug_line("home panel event")
    response = client.get("/ui/home/debug-log")
    assert response.status_code == 200
    assert "home panel event" in response.text
    assert "Debug" in response.text
    response = client.post("/ui/home/debug-log", data={"action": "disable", "limit": "25"})
    assert response.status_code == 200
    assert "Debug OFF" in response.text


def test_activity_log_endpoint_tracks_generate(monkeypatch, tmp_path):
    _prime_activity_log(monkeypatch, tmp_path)
    prev_state = debug_log.is_debug_enabled()
    debug_log.set_debug_enabled(False)
    try:
        response = client.post(
            "/api/interop/generate",
            data={"version": "hl7-v2-4", "trigger": "ADT_A01", "count": "1"},
            headers={"Accept": "text/plain"},
        )
        assert response.status_code == 200
        payload = client.get("/api/diag/activity").json()
        assert payload["count"] >= 1
        assert any("event=generate" in line for line in payload["lines"])
    finally:
        debug_log.set_debug_enabled(prev_state)


def test_activity_endpoint_html_response(monkeypatch, tmp_path):
    _prime_activity_log(monkeypatch, tmp_path)
    activity_log.log_activity("manual", note="ok")
    response = client.get("/api/diag/activity", params={"format": "html", "limit": "5"})
    assert response.status_code == 200
    assert "<pre" in response.text
    assert "manual" in response.text


def test_http_logging_respects_debug_toggle(tmp_path):
    app = FastAPI()

    @app.get("/ping")
    async def _ping():
        return {"ok": True}

    log_path = tmp_path / "http.log"
    install_http_logging(app, log_path=log_path)
    local_client = TestClient(app)
    prev_state = debug_log.is_debug_enabled()
    try:
        debug_log.set_debug_enabled(True)
        local_client.get("/ping")
        assert log_path.exists()
        contents = log_path.read_text(encoding="utf-8")
        assert "Action=GET /ping" in contents
        debug_log.set_debug_enabled(False)
        local_client.get("/ping")
        assert log_path.read_text(encoding="utf-8") == contents
    finally:
        debug_log.set_debug_enabled(prev_state)
