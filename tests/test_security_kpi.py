import json
from pathlib import Path
from fastapi.testclient import TestClient
from starlette.templating import Jinja2Templates
from api.ui import install_link_for
from main import app
import api.security as security


def test_security_summary_and_index(monkeypatch, tmp_path):
    repo_templates = Path(__file__).resolve().parents[1] / "templates"
    monkeypatch.chdir(tmp_path)
    security.templates = Jinja2Templates(directory=str(repo_templates))
    install_link_for(security.templates)
    d = tmp_path / "out/security/ui/recon/active"
    d.mkdir(parents=True)
    obj = {
        "profile": "safe",
        "inventory": {
            "hosts": ["h"],
            "services": [
                {
                    "port": 80,
                    "service": "http",
                    "cves": [{"id": "CVE-X", "cvss": 7.5, "kev": True}],
                }
            ],
        },
    }
    (d / "a.json").write_text(json.dumps(obj))

    c = TestClient(app)
    r = c.get("/security/summary")
    assert r.status_code == 200
    t = r.text
    assert "Recon" in t and "Severities" in t and "Netforensics" in t
    assert (tmp_path / "out/security/ui/index.json").exists()
