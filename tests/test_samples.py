from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.interop import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_list_samples_default():
    r = client.get("/api/interop/samples")
    assert r.status_code == 200
    data = r.json()
    assert data["version"] == "hl7-v2-4"
    assert isinstance(data["items"], list)
    assert len(data["items"]) > 0
    assert "trigger" in data["items"][0]
    assert "relpath" in data["items"][0]


def test_search_specific():
    r = client.get("/api/interop/samples", params={"version": "hl7-v2-3", "q": "ADT_A01"})
    assert r.status_code == 200
    items = r.json()["items"]
    assert any("ADT_A01" in it["trigger"] for it in items)


def test_get_sample_by_relpath():
    listing = client.get("/api/interop/samples").json()
    relpath = listing["items"][0]["relpath"]
    r = client.get("/api/interop/sample", params={"relpath": relpath})
    assert r.status_code == 200
    body = r.json()
    assert "MSH" in body["text"]
    assert body["relpath"] == relpath
