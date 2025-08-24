import os
import subprocess
import sys
from pathlib import Path

from silhouette_core.patch.propose import propose_patch

FIXTURE = Path('tests/fixtures/patch_repo').resolve()


def test_propose_patch_generates_diff(monkeypatch):
    monkeypatch.chdir(FIXTURE)
    res = propose_patch('remove unused param', hints=['src/util.py'])
    assert res['diff']
    assert res['summary']['insertions'] == 1
    assert res['summary']['deletions'] == 0
    assert 'src/util.py' in res['summary']['files_changed']


def test_propose_patch_deterministic(monkeypatch):
    monkeypatch.chdir(FIXTURE)
    res1 = propose_patch('remove unused param', hints=['src/util.py'])
    res2 = propose_patch('remove unused param', hints=['src/util.py'])
    assert res1 == res2


def test_policy_filters_protected(monkeypatch):
    monkeypatch.chdir(FIXTURE)
    res = propose_patch('tweak ci', hints=['.github/workflows/ci.yml'])
    assert res['diff'] == ''
    assert any('protected path' in n for n in res['notes'])


def test_cli_produces_artifacts(monkeypatch):
    monkeypatch.chdir(FIXTURE)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    subprocess.check_call([
        sys.executable,
        '-m',
        'silhouette_core.cli',
        'propose',
        'patch',
        '--goal',
        'remove unused param',
        '--hint',
        'src/util.py',
    ], env=env)
    artifact_dirs = sorted(Path('artifacts').glob('*'))
    assert artifact_dirs
    files = {p.name for p in artifact_dirs[-1].iterdir()}
    assert {
        'proposed_patch.diff',
        'impact_set.json',
        'proposed_pr_body.md',
    } <= files


def test_cli_exit_nonzero_on_protected(monkeypatch):
    monkeypatch.chdir(FIXTURE)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    proc = subprocess.run([
        sys.executable,
        '-m',
        'silhouette_core.cli',
        'propose',
        'patch',
        '--goal',
        'tweak ci',
        '--hint',
        '.github/workflows/ci.yml',
    ], capture_output=True, text=True, env=env)
    assert proc.returncode != 0
