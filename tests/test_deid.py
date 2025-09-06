from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.interop_gen import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_deid_changes_pid():
    txt = "MSH|^~\\&|A|B|C|D|202501010000||ADT^A01|X|P|2.4\r\nPID|1||12345^^^HOSP^MR||DOE^JOHN||||||||||||"
    r = client.post("/api/interop/deidentify", json={"text": txt, "seed": 42})
    out = r.json()["text"]
    assert "PID|" in out and out != txt
