import pytest
from fastapi.testclient import TestClient
from server import app

client = TestClient(app)

def test_generate_not_shadowed_get():
    r = client.get("/api/interop/generate", params={"version":"hl7-v2-4","trigger":"ADT_A03","count":1})
    assert r.status_code == 200
    assert r.text.startswith("MSH|")

def test_generate_not_shadowed_post_form():
    r = client.post(
        "/api/interop/generate",
        data={"version":"hl7-v2-4","trigger":"ADT_A03","count":"1"},
        headers={"Accept":"text/plain"}
    )
    assert r.status_code == 200
    assert r.text.startswith("MSH|")

def test_exec_catch_all_moved():
    r = client.post("/api/interop/someTool", json={"foo":"bar"})
    assert r.status_code in (404, 405)
    r2 = client.post("/api/interop/exec/someTool", json={"foo":"bar"})
    assert r2.status_code in (200, 400, 404)
