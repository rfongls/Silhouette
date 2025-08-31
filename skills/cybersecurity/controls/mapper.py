import json
from pathlib import Path
import yaml


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
    (controls_dir / 'coverage.json').write_text(json.dumps({'controls': coverage}, indent=2))

    # simple HTML
    rows = '\n'.join(
        f"<tr><td>{c['id']}</td><td>{c['description']}</td><td>{c['status']}</td></tr>"
        for c in coverage
    )
    html = f"<html><body><table><tr><th>ID</th><th>Description</th><th>Status</th></tr>{rows}</table></body></html>"
    (controls_dir / 'coverage.html').write_text(html)
