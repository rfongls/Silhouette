import json
from pathlib import Path
from collections import Counter
from ..enrich.cve_cache import get_cve, is_kev


def _load_findings(run_dir: Path):
    findings = []
    scans_dir = run_dir / 'scans'
    if not scans_dir.exists():
        return findings
    for tool_dir in scans_dir.iterdir():
        norm = tool_dir / 'normalized.json'
        if norm.exists():
            data = json.loads(norm.read_text())
            findings.extend(data.get('findings', []))
    return findings


def write_report(run_dir: Path, fmt: str) -> None:
    report_dir = run_dir / 'report'
    report_dir.mkdir(parents=True, exist_ok=True)
    findings = _load_findings(run_dir)
    severities = Counter(f['severity'] for f in findings)

    lines = ["# Security Report", "", "## Severity Counts"]
    for sev, count in severities.items():
        lines.append(f"- {sev}: {count}")
    lines.append("\n## Findings")
    for f in findings:
        lines.append(f"### {f['title']} ({f['severity']})")
        lines.append(f"Tool: {f['tool']}  ")
        lines.append(f"Description: {f['description']}  ")
        ids = f.get('identifiers', [])
        if ids:
            refs = []
            for i in ids:
                refs.append(i)
                cve = get_cve(i) if i.startswith('CVE') else None
                if cve:
                    refs.append(f"CVSS: {cve.get('cvss')}")
                    if is_kev(i):
                        refs.append('KEV')
            lines.append('Identifiers: ' + ', '.join(refs))
        lines.append('')
    md_path = report_dir / 'report.md'
    md_path.write_text('\n'.join(lines))
    html_path = report_dir / 'report.html'
    html_body = '<br/>'.join(lines)
    html_path.write_text(f"<html><body>{html_body}</body></html>")
    if fmt == 'pdf':
        pdf_path = report_dir / 'report.pdf.txt'
        pdf_path.write_text('PDF generation not available; see report.html')
