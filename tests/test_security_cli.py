import subprocess
import sys
from pathlib import Path


def run_cmd(args):
    return subprocess.run([sys.executable, '-m', 'silhouette_core.cli'] + args, capture_output=True, text=True)


def test_help_shows_policy_banner():
    r = run_cmd(['security', '--help'])
    assert r.returncode == 0
    assert 'Authorized use only' in r.stdout


def test_pentest_requires_ack():
    r = run_cmd(['security', 'pentest', 'recon'])
    assert r.returncode != 0
    assert 'Authorized use only' in (r.stdout + r.stderr)


def test_capture_dry_run():
    r = run_cmd(['security', 'capture', '--dry-run'])
    assert r.returncode == 0
