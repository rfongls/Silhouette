from pathlib import Path

from silhouette_core.impact.impact_set import compute_impact

FIXTURE = Path('tests/fixtures/patch_repo')


def test_compute_impact(monkeypatch):
    monkeypatch.chdir(FIXTURE)
    impact = compute_impact(['src/util.py'])
    assert 'src/util.py' in impact['modules']
    assert impact['tests']['must_run'] == ['tests/test_util.py']
    assert 'services/api/README.md' in impact['docs']['suggested']
    assert impact == compute_impact(['src/util.py'])
