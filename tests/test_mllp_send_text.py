from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.interop_gen as ig

app = FastAPI()
app.include_router(ig.router)
client = TestClient(app)

def test_mllp_send_accepts_string_and_splits_blank_lines(monkeypatch):
    def fake_send(host, port, messages, timeout=5.0):
        return [f"ACK-{i}" for i, _ in enumerate(messages)]
    monkeypatch.setattr(ig, "send_mllp_batch", fake_send)

    payload = {
        "host": "127.0.0.1",
        "port": 2575,
        "messages": (
            "MSH|^~\\&|A|B|C|D|202501010000||ADT^A01|X|P|2.4\r\nPID|1||123||DOE^JOHN\r\n"
            "\r\n"
            "MSH|^~\\&|A|B|C|D|202501010001||ADT^A03|Y|P|2.4\r\nPID|1||456||DOE^JANE\r\n"
        ),
        "timeout": 3.0,
    }
    r = client.post("/api/interop/mllp/send", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["sent"] == 2
    assert len(data["acks"]) == 2
