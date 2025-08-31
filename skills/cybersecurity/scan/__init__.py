import json
from pathlib import Path

from ..normalize.normalizer import normalize_generic


def dispatch_scan(tool: str, target: str, run_dir: Path, use_seed: bool, exec_real: bool, dry_run: bool) -> None:
    scans_dir = run_dir / 'scans' / tool
    raw_dir = scans_dir / 'raw'
    raw_dir.mkdir(parents=True, exist_ok=True)
    norm_path = scans_dir / 'normalized.json'

    if dry_run:
        raw = {}
    else:
        if use_seed or not exec_real:
            seed_path = Path(f'data/security/seeds/samples/{tool}/sample.json')
            raw = json.loads(seed_path.read_text())
        else:
            raw = {}  # real execution not implemented
    (raw_dir / 'result.json').write_text(json.dumps(raw, indent=2))
    normalized = normalize_generic(tool, raw)
    norm_path.write_text(json.dumps({'findings': normalized}, indent=2))
