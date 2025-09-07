from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.interop_gen import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_generate_is_deterministic_with_seed():
    body = {
        "version": "hl7-v2-4",
        "template_relpath": "hl7-v2-4/ADT_A01.hl7",
        "count": 5,
        "seed": 999,
        "ensure_unique": True,
        "include_clinical": True,
        "deidentify": True,
        "output_format": "ndjson",
    }
    r1 = client.post("/api/interop/generate", json=body).text
    r2 = client.post("/api/interop/generate", json=body).text
    assert r1 == r2
