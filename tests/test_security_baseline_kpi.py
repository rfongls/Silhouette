import json
from fastapi.testclient import TestClient
from main import app
import api.security as security


def test_security_summary_and_index(monkeypatch, tmp_path):
    monkeypatch.setattr(security, "OUT_ROOT", tmp_path / 'out/security')
    monkeypatch.setattr(security, "UI_OUT", tmp_path / 'out/security/ui')
    monkeypatch.setattr(security, "INDEX_PATH", tmp_path / 'out/security/ui/index.json')
    c = TestClient(app)
    d = security.UI_OUT / 'recon/active'
    d.mkdir(parents=True)
    d.joinpath('x.json').write_text(json.dumps({'profile':'safe','inventory':{'hosts':['h'], 'services':[{'port':80,'service':'http','cves':[{'id':'CVE-X','cvss':7.5}]}]}}))
    r = c.get('/security/summary')
    assert r.status_code == 200
    assert (security.INDEX_PATH).exists()
