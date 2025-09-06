from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.interop_gen import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_generate_single_from_template():
    body = {
        "version": "hl7-v2-4",
        "template_relpath": "hl7-v2-4/ADT_A01.hl7",
        "count": 3,
        "seed": 123,
        "ensure_unique": True,
        "include_clinical": True,
        "deidentify": True,
        "output_format": "ndjson",
    }
    r = client.post("/api/interop/generate", json=body)
    assert r.status_code == 200
    lines = r.text.strip().splitlines()
    assert len(lines) == 3
    ids = set()
    import json as _json

    for line in lines:
        obj = _json.loads(line)
        hl7 = obj["hl7"]
        msh = next(l for l in hl7.splitlines() if l.startswith("MSH|"))
        mcid = msh.split("|")[9]
        ids.add(mcid)
    assert len(ids) == 3
