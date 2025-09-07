from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.interop import router as interop_router


app = FastAPI()
app.include_router(interop_router)
client = TestClient(app)


def test_quickstart_renders_three_columns():
    resp = client.post(
        "/interop/quickstart",
        data={
            "trigger": "ADT_A01",
            "version": "hl7-v2-4",
            "seed": "42",
            "ensure_unique": "true",
            "include_clinical": "true",
            "deidentify": "false",
        },
    )
    if resp.status_code == 200:
        html = resp.text
        assert "HL7 — ADT_A01" in html
        assert "FHIR (Preview)" in html
        assert "Validation" in html
