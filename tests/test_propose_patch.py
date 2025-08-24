from pathlib import Path

from silhouette_core.patch.propose import propose_patch

FIXTURE = Path('tests/fixtures/patch_repo')


def test_propose_patch_generates_diff(monkeypatch):
    monkeypatch.chdir(FIXTURE)
    res = propose_patch('remove unused param', hints=['src/util.py'])
    assert res['diff']
    assert res['summary']['insertions'] == 1
    assert res['summary']['deletions'] == 0
    assert 'src/util.py' in res['summary']['files_changed']


def test_policy_filters_protected(monkeypatch):
    monkeypatch.chdir(FIXTURE)
    res = propose_patch('tweak ci', hints=['.github/workflows/ci.yml'])
    assert res['diff'] == ''
    assert any('protected path' in n for n in res['notes'])
