import json

from silhouette_core.skills.cyber_common import Deny, require_auth_and_scope
from silhouette_core.skills.cyber_zap_baseline.v1.wrapper import tool as zap_run
from silhouette_core.skills.cyber_trivy_scan.v1.wrapper import tool as trivy_run
from silhouette_core.skills.cyber_checkov_scan.v1.wrapper import tool as checkov_run
from silhouette_core.skills.cyber_cis_audit.v1.wrapper import tool as cis_run
from silhouette_core.skills.cyber_control_mapper.v1.wrapper import tool as map_run
from silhouette_core.skills.cyber_reference_cdse.v1.wrapper import tool as ref_run
from silhouette_core.skills.cyber_report_writer.v1.wrapper import tool as report_run


def _load_sample(path):
    import pathlib, json as j
    p = pathlib.Path(path)
    return j.loads(p.read_text()) if p.exists() else None


def tool(payload: str) -> str:
    """
    Input JSON:
    {
      "task":"web_baseline",
      "target":"https://in-scope.example",
      "scope_file":"docs/cyber/scope_example.txt",
      "dry_run": true,
      "trivy_target":"alpine:3.19",
      "checkov_dir":"./infra"
    }
    Output: {"ok":true,"report_md":"artifacts/cyber/reports/report_*.md"}
    """
    args = json.loads(payload or "{}")
    task = args.get("task", "web_baseline")
    target = args.get("target", "")
    scope_file = args.get("scope_file", "docs/cyber/scope_example.txt")
    dry_run = bool(args.get("dry_run", False))

    try:
        require_auth_and_scope(scope_file, target)
        findings = {}

        if dry_run:
            findings["zap"] = _load_sample("docs/cyber/samples/zap_web_baseline_sample.json") or {"dry_run": True}
        else:
            z = json.loads(zap_run(json.dumps({"url": target, "scope_file": scope_file, "time": 2})))
            findings["zap"] = z

        if args.get("trivy_target") or args.get("dir"):
            if dry_run:
                findings["trivy"] = _load_sample("docs/cyber/samples/trivy_fs_sample.json") or {"dry_run": True}
            else:
                t = json.loads(trivy_run(json.dumps({"target": args.get("trivy_target"), "dir": args.get("dir")})))
                findings["trivy"] = t

        if args.get("checkov_dir"):
            if dry_run:
                findings["checkov"] = {"stdout": (_load_sample("docs/cyber/samples/checkov_sample.json") or "DRY RUN")}
            else:
                c = json.loads(checkov_run(json.dumps({"dir": args.get("checkov_dir")})))
                findings["checkov"] = c

        if dry_run:
            findings["cis"] = _load_sample("docs/cyber/samples/cis_audit_sample.json") or {"dry_run": True}
        else:
            cis = json.loads(cis_run("{}"))
            findings["cis"] = cis

        flat = list(findings.values())
        mapped = json.loads(map_run(json.dumps(flat)))

        refs = json.loads(ref_run("baseline configuration"))
        references = refs.get("results", [])

        report = {
            "task": task,
            "scope": {"targets": [target], "scope_file": scope_file},
            "findings": findings,
            "mappings": mapped.get("mappings", []),
            "references": references,
        }
        rep = json.loads(report_run(json.dumps(report)))
        return json.dumps({"ok": True, "report_md": rep.get("report_md")})

    except Deny as e:
        return json.dumps({"ok": False, "deny": str(e)})
