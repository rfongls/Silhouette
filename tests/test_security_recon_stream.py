import json
from fastapi.testclient import TestClient
from main import app


def test_recon_bulk_stream_order(monkeypatch):
    import api.security as sec

    def fake_recon(payload: str):
        data = json.loads(payload)
        return json.dumps({"target": data["target"]})

    monkeypatch.setattr(sec, "recon_tool", fake_recon)

    client = TestClient(app)
    targets = "a.example.com\nb.example.com"
    with client.stream("GET", "/security/recon-bulk-stream", params={"targets": targets}) as resp:
        lines = [line.strip() for line in resp.iter_lines() if line.strip()]
    events = [json.loads(line.split("data: ", 1)[1]) for line in lines]
    assert events[0] == {"event": "start", "count": 2}
    assert events[1]["event"] == "item" and events[1]["index"] == 1
    assert events[2]["event"] == "item" and events[2]["index"] == 2
    assert events[3] == {"event": "done"}
