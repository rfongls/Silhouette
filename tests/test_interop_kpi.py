import json
from fastapi.testclient import TestClient
from main import app
import api.interop as interop


def test_interop_summary_oob(monkeypatch, tmp_path):
    monkeypatch.setattr(interop, "OUT_ROOT", tmp_path / 'out/interop')
    monkeypatch.setattr(interop, "UI_OUT", tmp_path / 'out/interop/ui')
    monkeypatch.setattr(interop, "INDEX_PATH", tmp_path / 'out/interop/ui/index.json')
    c = TestClient(app)
    tdir = interop.UI_OUT / 'translate/active'
    vdir = interop.UI_OUT / 'validate/active'
    tdir.mkdir(parents=True)
    vdir.mkdir(parents=True)
    tdir.joinpath('1.json').write_text(json.dumps({'kind':'translate','rc':0,'stdout':'','stderr':''}))
    vdir.joinpath('2.json').write_text(json.dumps({'kind':'validate','rc':0,'stdout':'','stderr':''}))
    r = c.get('/interop/summary')
    assert r.status_code == 200
    assert 'Translate' in r.text and 'Validate' in r.text
