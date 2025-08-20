import json, pathlib, time

OUTDIR = pathlib.Path("artifacts/cyber/reports"); OUTDIR.mkdir(parents=True, exist_ok=True)

def tool(payload: str) -> str:
    """
    Input: {
      "task": "web_baseline",
      "scope": {"targets":[...]},
      "findings": {"nmap":{...},"zap":{...},"trivy":{...},"checkov":{...},"cis":{...}},
      "mappings": [{"finding":...,"controls":[...]}],
      "references": [{"ref":"[1]","doc_id":...,"section_id":...,"snippet":...}]
    }
    Output: {"ok":true,"report_md": ".../report_*.md"}
    """
    data = json.loads(payload or "{}")
    ts = int(time.time())
    md = [f"# Security Assessment Report — {data.get('task','task')}", ""]
    md += ["## Scope", "```json", json.dumps(data.get("scope",{}), indent=2), "```", ""]
    md += ["## Findings", "```json", json.dumps(data.get("findings",{}), indent=2), "```", ""]
    md += ["## Control Mapping", "```json", json.dumps(data.get("mappings",[]), indent=2), "```", ""]
    if data.get("references"):
        md += ["## References"]
        for r in data["references"]:
            md.append(f"- {r['ref']} {r['doc_id']} #{r['section_id']}: {r['snippet'][:160]}…")
    path = OUTDIR / f"report_{ts}.md"
    path.write_text("\n".join(md), encoding="utf-8")
    return json.dumps({"ok": True, "report_md": str(path)})
