import json
from pathlib import Path
from typing import Any, Dict, List

SEVERITY_MAP = {
    'UNKNOWN': 'info',
    'LOW': 'low',
    'MEDIUM': 'medium',
    'HIGH': 'high',
    'CRITICAL': 'critical',
}


def normalize_generic(tool: str, raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    if tool == 'trivy':
        for result in raw.get('results', []):
            target = result.get('Target')
            for vuln in result.get('Vulnerabilities', []) or []:
                findings.append({
                    'tool': tool,
                    'target': target,
                    'title': vuln.get('Title', ''),
                    'description': vuln.get('Description', ''),
                    'severity': SEVERITY_MAP.get(vuln.get('Severity', '').upper(), 'info'),
                    'category': 'container/vuln',
                    'location': '',
                    'evidence': {},
                    'identifiers': [vuln.get('VulnerabilityID')],
                    'recommended_action': '',
                })
    elif tool == 'checkov':
        for res in raw.get('results', []):
            findings.append({
                'tool': tool,
                'target': res.get('file_path'),
                'title': res.get('check_id'),
                'description': res.get('check_name', ''),
                'severity': SEVERITY_MAP.get(res.get('severity', '').upper(), 'info'),
                'category': 'iac/misconfig',
                'location': res.get('resource', ''),
                'evidence': {},
                'identifiers': [res.get('check_id')],
                'recommended_action': res.get('guideline', ''),
            })
    elif tool == 'grype':
        for match in raw.get('matches', []):
            vuln = match.get('vulnerability', {})
            art = match.get('artifact', {})
            vid = vuln.get('id')
            findings.append({
                'tool': tool,
                'target': art.get('name'),
                'title': vid or '',
                'description': vuln.get('description', ''),
                'severity': SEVERITY_MAP.get(vuln.get('severity', '').upper(), 'info'),
                'category': 'container/vuln',
                'location': '',
                'evidence': {},
                'identifiers': [vid] if vid else [],
                'recommended_action': '',
            })
    elif tool == 'tfsec':
        for r in raw.get('results', []):
            findings.append({
                'tool': tool,
                'target': r.get('location', ''),
                'title': r.get('rule_id', ''),
                'description': '',
                'severity': SEVERITY_MAP.get(r.get('severity', '').upper(), 'info'),
                'category': 'iac/misconfig',
                'location': r.get('resource', ''),
                'evidence': {},
                'identifiers': [r.get('rule_id')],
                'recommended_action': '',
            })
    elif tool == 'kics':
        for q in raw.get('queries', []):
            files = q.get('files', []) or [{}]
            f = files[0]
            findings.append({
                'tool': tool,
                'target': f.get('fileName', ''),
                'title': q.get('id', ''),
                'description': q.get('issue', ''),
                'severity': SEVERITY_MAP.get(q.get('severity', '').upper(), 'info'),
                'category': 'iac/misconfig',
                'location': f.get('fileName', ''),
                'evidence': {},
                'identifiers': [q.get('id')],
                'recommended_action': '',
            })
    elif tool == 'lynis':
        for w in raw.get('warnings', []):
            findings.append({
                'tool': tool,
                'target': '',
                'title': w.get('id', ''),
                'description': w.get('description', ''),
                'severity': SEVERITY_MAP.get(w.get('severity', '').upper(), 'info'),
                'category': 'host/baseline',
                'location': '',
                'evidence': {},
                'identifiers': [w.get('id')],
                'recommended_action': '',
            })
    elif tool == 'gitleaks':
        for f in raw.get('findings', []):
            findings.append({
                'tool': tool,
                'target': f.get('file', ''),
                'title': f.get('rule', ''),
                'description': '',
                'severity': SEVERITY_MAP.get(f.get('severity', '').upper(), 'info'),
                'category': 'secrets',
                'location': f.get('file', ''),
                'evidence': {},
                'identifiers': [],
                'recommended_action': '',
            })
    elif tool == 'pip_audit':
        for d in raw.get('dependencies', []):
            for v in d.get('vulns', []) or []:
                findings.append({
                    'tool': tool,
                    'target': d.get('name', ''),
                    'title': v.get('id', ''),
                    'description': '',
                    'severity': SEVERITY_MAP.get(v.get('severity', '').upper(), 'info'),
                    'category': 'sca',
                    'location': d.get('version', ''),
                    'evidence': {},
                    'identifiers': [v.get('id')],
                    'recommended_action': '',
                })
    elif tool == 'npm_audit':
        for a in raw.get('advisories', []):
            ids = a.get('cves') or []
            sev = a.get('severity', '').upper()
            findings.append({
                'tool': tool,
                'target': a.get('module_name', ''),
                'title': ids[0] if ids else a.get('module_name', ''),
                'description': '',
                'severity': SEVERITY_MAP.get(sev, 'info'),
                'category': 'sca',
                'location': '',
                'evidence': {},
                'identifiers': ids,
                'recommended_action': '',
            })
    else:
        findings.append({'tool': tool, 'target': '', 'title': 'stub', 'description': '', 'severity': 'info', 'category': '', 'location': '', 'evidence': {}, 'identifiers': [], 'recommended_action': ''})
    return findings
