import json
from pathlib import Path
from skills.cybersecurity.normalize.normalizer import normalize_generic


def test_normalizer_keys():
    raw = {
        "results": [
            {
                "Target": "x",
                "Vulnerabilities": [
                    {
                        "VulnerabilityID": "CVE-0001",
                        "Title": "a",
                        "Description": "b",
                        "Severity": "HIGH",
                    }
                ],
            }
        ]
    }
    res = normalize_generic('trivy', raw)
    required = {
        'tool', 'target', 'title', 'description', 'severity',
        'category', 'location', 'evidence', 'identifiers', 'recommended_action'
    }
    assert required <= res[0].keys()


def test_normalizer_grype():
    raw = {
        "matches": [
            {
                "artifact": {"name": "pkg"},
                "vulnerability": {
                    "id": "CVE-1", "description": "x", "severity": "HIGH"
                },
            }
        ]
    }
    res = normalize_generic('grype', raw)
    assert res[0]['severity'] == 'high'


def test_normalizer_all_seeds():
    tools = [
        'trivy', 'checkov', 'grype', 'tfsec', 'kics', 'lynis', 'gitleaks', 'pip_audit', 'npm_audit'
    ]
    required = {
        'tool', 'target', 'title', 'description', 'severity',
        'category', 'location', 'evidence', 'identifiers', 'recommended_action'
    }
    for tool in tools:
        path = Path(f'data/security/seeds/samples/{tool}/sample.json')
        raw = json.loads(path.read_text())
        findings = normalize_generic(tool, raw)
        assert findings, tool
        assert required <= findings[0].keys()