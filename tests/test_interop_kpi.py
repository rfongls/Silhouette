import json
from pathlib import Path
from fastapi.testclient import TestClient
from starlette.templating import Jinja2Templates
from api.ui import install_link_for
from main import app
import api.interop as interop

def test_interop_summary_and_index(monkeypatch, tmp_path):
    repo_templates = Path(__file__).resolve().parents[1] / "templates"
    monkeypatch.chdir(tmp_path)
    interop.templates = Jinja2Templates(directory=str(repo_templates))
    install_link_for(interop.templates)
    # seed artifacts
    (tmp_path / "out/interop/ui/send/active").mkdir(parents=True)
    (tmp_path / "out/interop/ui/translate/active").mkdir(parents=True)
    (tmp_path / "out/interop/ui/validate/active").mkdir(parents=True)
    (tmp_path / "out/interop/ui/send/active/1.json").write_text(
        json.dumps({"kind": "send", "ack": "MSH\rMSA|AA|X", "ack_ok": True})
    )
    (tmp_path / "out/interop/ui/translate/active/2.json").write_text(
        json.dumps({"kind": "translate", "rc": 0, "stdout": "", "stderr": ""})
    )
    (tmp_path / "out/interop/ui/validate/active/3.json").write_text(
        json.dumps({"kind": "validate", "rc": 0, "stdout": "", "stderr": ""})
    )

    c = TestClient(app)
    r = c.get("/interop/summary")
    assert r.status_code == 200
    t = r.text
    assert "Interop Metrics" in t
    assert "Reports" in t
