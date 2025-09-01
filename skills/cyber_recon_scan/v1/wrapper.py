import json
from skills.cyber_common import require_auth_and_scope, write_result, Deny


def _enrich_services(services: list[dict]) -> list[dict]:
    """Offline enrichment stub for discovered services."""
    for svc in services:
        if svc.get("service") == "http":
            svc.setdefault("cves", []).append("CVE-2023-0001")
    return services


def tool(payload: str) -> str:
    """Perform placeholder recon on the target.

    Input JSON: {"target":"example.com","scope_file":"scope.txt","profile":"safe","out_dir":"out/security/..."}
    """
    args = json.loads(payload or "{}")
    target = args.get("target", "")
    scope_file = args.get("scope_file", "scope.txt")
    profile = args.get("profile", "safe")
    out_dir = args.get("out_dir")
    try:
        require_auth_and_scope(scope_file, target)
        services = []
        if profile in {"version", "full"}:
            services.append({"port": 80, "service": "http"})
        if profile == "full":
            services.append({"port": 443, "service": "https"})
        services = _enrich_services(services)
        inventory = {"hosts": [target], "services": services}
        data = {"target": target, "profile": profile, "inventory": inventory}
        path = write_result("recon", data, run_dir=out_dir)
        return json.dumps({"ok": True, "result": path})
    except Deny as e:
        return json.dumps({"ok": False, "deny": str(e)})
