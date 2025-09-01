import json
from pathlib import Path
import yaml
import csv


def map_controls(framework: str, evidence_dir: Path, run_dir: Path) -> None:
    cfg_path = Path(f'configs/security/controls/{framework}.yaml')
    data = yaml.safe_load(cfg_path.read_text())
    controls = data.get('controls', [])

    manifest = json.loads((evidence_dir / 'manifest.json').read_text())
    present = {f['file'] for f in manifest.get('files', [])}

    coverage = []
    for ctl in controls:
        evidence_file = ctl.get('evidence')
        status = 'met' if evidence_file in present else 'missing'
        coverage.append({'id': ctl.get('id'), 'description': ctl.get('description'), 'status': status})

    controls_dir = run_dir / 'controls'
    controls_dir.mkdir(exist_ok=True, parents=True)
    payload = {'controls': coverage}
    (controls_dir / 'coverage.json').write_text(json.dumps(payload, indent=2))

    # simple HTML
    rows = '\n'.join(
        f"<tr><td>{c['id']}</td><td>{c['description']}</td><td>{c['status']}</td></tr>"
        for c in coverage
    )
    html = f"<html><body><table><tr><th>ID</th><th>Description</th><th>Status</th></tr>{rows}</table></body></html>"
    (controls_dir / 'coverage.html').write_text(html)

    # CSV export
    with (controls_dir / 'coverage.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['id', 'description', 'status', 'evidence'])
        w.writeheader()
        evidence_lookup = {c['id']: c.get('evidence', '') for c in controls}
        for c in coverage:
            w.writerow({
                'id': c['id'],
                'description': c['description'],
                'status': c['status'],
                'evidence': evidence_lookup.get(c['id'], '')
            })