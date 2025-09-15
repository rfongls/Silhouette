import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from server import app


client = TestClient(app)


def test_interop_dashboard_renders():
    response = client.get("/ui/interop/dashboard")
    assert response.status_code == 200
    assert "Generate Messages" in response.text


def test_diag_routes_available():
    response = client.get("/api/diag/routes")
    assert response.status_code == 200
    data = response.json()
    assert any(route["path"] == "/api/interop/generate" for route in data.get("routes", []))
