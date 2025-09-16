import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from server import app
from api import debug_log


client = TestClient(app)


def _prime_debug_log(monkeypatch, tmp_path):
    monkeypatch.setattr(debug_log, "LOG_FILE", tmp_path / "generator_debug.log")
    debug_log.reset_debug_log(clear_file=True)
    debug_log.set_debug_enabled(True)
    debug_log.reset_debug_log(clear_file=True)


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
