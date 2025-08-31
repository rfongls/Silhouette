import csv
import json
import shutil
import re
import zipfile
from pathlib import Path
from typing import Iterable

from ..util.io import RunIO


def _load_redact_rules(path: Path) -> Iterable[re.Pattern]:
    if not path.exists():
        return []
    import yaml
    data = yaml.safe_load(path.read_text()) or {}
    patterns = []
    for rule in data.get('patterns', []):
        patterns.append(re.compile(rule['regex']))
    return patterns


def _redact_text(text: str, patterns: Iterable[re.Pattern]) -> str:
    redacted = text
    for pat in patterns:
        redacted = pat.sub('[REDACTED]', redacted)
    return redacted


def collect_evidence(source: Path, run_dir: Path) -> Path:
    evidence_dir = run_dir / 'evidence'
    originals = evidence_dir / 'originals'
    redacted = evidence_dir / 'redacted'
    pack_dir = run_dir / 'evidence_packs'
    originals.mkdir(parents=True, exist_ok=True)
    redacted.mkdir(parents=True, exist_ok=True)
    pack_dir.mkdir(parents=True, exist_ok=True)

    # copy originals
    for file in source.rglob('*'):
        if file.is_file():
            dst = originals / file.relative_to(source)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, dst)

    runio = RunIO()
    # checksums and manifest
    entries = []
    checksums = []
    patterns = _load_redact_rules(Path('configs/security/redact_rules.yaml'))
    for file in originals.rglob('*'):
        if file.is_file():
            rel = file.relative_to(originals).as_posix()
            checksum = runio.sha256sum(file)
            entries.append({'file': rel})
            checksums.append({'file': rel, 'sha256': checksum})
            text = file.read_text(errors='ignore')
            red_text = _redact_text(text, patterns)
            out_file = redacted / rel
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(red_text)

    # write manifest and checksums
    manifest_path = evidence_dir / 'manifest.json'
    manifest_path.write_text(json.dumps({'files': entries}, indent=2))
    checksums_path = evidence_dir / 'checksums.csv'
    with checksums_path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['file', 'sha256'])
        writer.writeheader()
        writer.writerows(checksums)

    # initial evidence pack
    build_evidence_pack(run_dir)
    return evidence_dir


def build_evidence_pack(run_dir: Path) -> Path:
    evidence_dir = run_dir / 'evidence'
    pack_dir = run_dir / 'evidence_packs'
    pack_dir.mkdir(parents=True, exist_ok=True)
    pack_path = pack_dir / 'pack.zip'
    with zipfile.ZipFile(pack_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for src, arcbase in [
            (evidence_dir / 'originals', 'evidence/originals'),
            (evidence_dir / 'redacted', 'evidence/redacted'),
        ]:
            if src.exists():
                for f in src.rglob('*'):
                    if f.is_file():
                        z.write(f, f"{arcbase}/{f.relative_to(src)}")
        for name in ['manifest.json', 'checksums.csv']:
            p = evidence_dir / name
            if p.exists():
                z.write(p, f"evidence/{name}")
        controls_dir = run_dir / 'controls'
        for name in ['coverage.json', 'coverage.html']:
            p = controls_dir / name
            if p.exists():
                z.write(p, f"controls/{name}")
        scans_dir = run_dir / 'scans'
        if scans_dir.exists():
            for norm in scans_dir.rglob('normalized.json'):
                tool = norm.parent.name
                z.write(norm, f"scans/{tool}/normalized.json")
        report_dir = run_dir / 'report'
        if report_dir.exists():
            for file in report_dir.glob('report.*'):
                z.write(file, f"report/{file.name}")
    return pack_path