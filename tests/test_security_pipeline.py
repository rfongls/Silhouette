import json
import subprocess
import sys
import zipfile
from pathlib import Path


def run(args):
    return subprocess.run([sys.executable, '-m', 'silhouette_core.cli'] + args, capture_output=True, text=True, check=True)


def test_pipeline(tmp_path):
    # evidence
    r = run(['security', 'evidence', '--source', 'docs/fixtures/security_sample'])
    run_dir = Path(r.stdout.strip().splitlines()[-1])
    # redaction
    redacted_log = run_dir / 'evidence' / 'redacted' / 'logs' / 'app.log'
    text = redacted_log.read_text()
    assert 'john.doe' not in text and '123-45-6789' not in text
    pack = run_dir / 'evidence_packs' / 'pack.zip'
    assert pack.exists()

    # map controls
    run(['security', '--out', str(run_dir), 'map-controls', '--framework', 'cis_v8', '--evidence', str(run_dir / 'evidence')])
    coverage = json.loads((run_dir / 'controls' / 'coverage.json').read_text())
    statuses = {c['id']: c['status'] for c in coverage['controls']}
    assert statuses['CIS-1'] == 'met'
    assert statuses['CIS-3'] == 'missing'
    assert (run_dir / 'controls' / 'coverage.csv').exists()

    # scan
    run(['security', '--out', str(run_dir), 'scan', '--tool', 'trivy', '--target', 'docs/fixtures/app', '--use-seed'])
    run(['security', '--out', str(run_dir), 'scan', '--tool', 'checkov', '--target', 'docs/fixtures/infra', '--use-seed'])
    run(['security', '--out', str(run_dir), 'scan', '--tool', 'grype', '--target', 'docs/fixtures/app', '--use-seed'])
    norm = json.loads((run_dir / 'scans' / 'trivy' / 'normalized.json').read_text())
    assert norm['findings'][0]['severity'] == 'high'

    # report
    run(['security', 'report', '--format', 'html', '--in', str(run_dir), '--offline'])
    assert (run_dir / 'report' / 'report.html').exists()
    # pack includes controls and normalized scans
    with zipfile.ZipFile(run_dir / 'evidence_packs' / 'pack.zip') as z:
        names = z.namelist()
        assert 'controls/coverage.json' in names
        assert 'scans/grype/normalized.json' in names
        assert 'controls/coverage.csv' in names
