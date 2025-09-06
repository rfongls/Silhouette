import json
from pathlib import Path

from fastapi.testclient import TestClient
from starlette.templating import Jinja2Templates

from main import app
import api.interop as interop


def test_validate_last_handles_empty(tmp_path, monkeypatch):
    repo_templates = Path(__file__).resolve().parents[1] / "templates"
    interop.templates = Jinja2Templates(directory=str(repo_templates))
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    resp = client.post("/interop/validate-last", data={"out_dir": "out/interop/ui"})
    assert resp.status_code == 200
    assert "No recent FHIR outputs" in resp.text


def test_translate_batch_writes_artifacts(tmp_path, monkeypatch):
    repo_templates = Path(__file__).resolve().parents[1] / "templates"
    interop.templates = Jinja2Templates(directory=str(repo_templates))
    monkeypatch.chdir(tmp_path)
    hlz1 = ("a.hl7", b"MSH|^~\\&|S|F|R|R|20250101||ADT^A01|X|P|2.5\rPID|1||1")
    hlz2 = ("b.hl7", b"MSH|^~\\&|S|F|R|R|20250101||ORU^R01|X|P|2.5\rPID|1||2\rOBR|1")
    client = TestClient(app)
    resp = client.post(
        "/interop/translate-batch",
        files=[("hl7_files", hlz1), ("hl7_files", hlz2)],
        data={"bundle": "transaction", "out_dir": "out/interop/ui", "validate_after": ""},
    )
    assert resp.status_code == 200
    assert (tmp_path / "out/interop/ui/translate/active").exists()
