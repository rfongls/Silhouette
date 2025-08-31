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
    else:
        findings.append({'tool': tool, 'target': '', 'title': 'stub', 'description': '', 'severity': 'info', 'category': '', 'location': '', 'evidence': {}, 'identifiers': [], 'recommended_action': ''})
    return findings
