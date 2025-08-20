import json, pathlib

MAP = pathlib.Path("docs/cyber/mappings/cdse_mappings.json")

def _load_map():
    if MAP.exists():
        return json.loads(MAP.read_text())
    return {
      "open port": ["System Management: Configuration Baselines"],
      "ssl": ["System Management: Encryption & TLS"],
      "critical vulnerability": ["Risk Management: Vulnerability Remediation"],
      "terraform": ["Supply Chain: IaC Security"],
      "kubernetes": ["System Management: Container/K8s Hardening"]
    }

def tool(findings_json: str) -> str:
    """
    Input: generic findings JSON
    Output: {"mappings":[{"finding":"...","controls":[...]}]}
    """
    fm = _load_map()
    findings = json.loads(findings_json or "[]")
    maps = []
    for f in findings:
        text = json.dumps(f).lower()
        matched = set()
        for key, controls in fm.items():
            if key in text:
                matched.update(controls)
        maps.append({"finding": f, "controls": sorted(matched)})
    return json.dumps({"ok": True, "mappings": maps})
