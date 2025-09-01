import json
from pathlib import Path
from skills.cyber_common import require_auth_and_scope, write_result, Deny

def _load_cache() -> dict:
    root = Path("data/security/seeds")
    cve_file = root / "cve" / "cve_seed.json"
    kev_file = root / "kev" / "kev_seed.json"
    cve = json.loads(cve_file.read_text()) if cve_file.exists() else {}
    kev = json.loads(kev_file.read_text()) if kev_file.exists() else {}
    return {"cve": len(cve), "kev": len(kev.get("cves", []))}


def _enrich_services(services: list[dict]) -> list[dict]:
    for svc in services:
        if svc.get("service") == "http":
            svc.setdefault("cves", []).append("CVE-0001")
    return services


def _load_cache() -> dict:
    root = Path("data/security/seeds")
    cve_file = root / "cve" / "cve_seed.json"
    kev_file = root / "kev" / "kev_seed.json"
    cve = json.loads(cve_file.read_text()) if cve_file.exists() else {}
    kev = json.loads(kev_file.read_text()) if kev_file.exists() else {}
    return {"cve": cve, "kev": set(kev.get("cves", []))}


def _enrich_services(services: list[dict], cache: dict) -> list[dict]:
    for svc in services:
        if svc.get("service") == "http":
            svc.setdefault("cves", ["CVE-0001"])
        details = []
        for cve in svc.get("cves", []):
            meta = cache["cve"].get(cve, {})
            details.append({"id": cve, "kev": cve in cache["kev"], **meta})
        if details:
            svc["cves"] = details
    return services


def _load_cache() -> dict:
    root = Path("data/security/seeds")
    cve_file = root / "cve" / "cve_seed.json"
    kev_file = root / "kev" / "kev_seed.json"
    cve = json.loads(cve_file.read_text()) if cve_file.exists() else {}
    kev = json.loads(kev_file.read_text()) if kev_file.exists() else {}
    return {"cve": cve, "kev": set(kev.get("cves", []))}


def _enrich_services(services: list[dict], cache: dict) -> list[dict]:
    for svc in services:
        if svc.get("service") == "http":
            svc.setdefault("cves", ["CVE-0001"])
        details = []
        for cve in svc.get("cves", []):
            meta = cache["cve"].get(cve, {})
            details.append({"id": cve, "kev": cve in cache["kev"], **meta})
        if details:
            svc["cves"] = details
    return services


def _load_cache() -> dict:
    root = Path("data/security/seeds")
    cve_file = root / "cve" / "cve_seed.json"
    kev_file = root / "kev" / "kev_seed.json"
    cve = json.loads(cve_file.read_text()) if cve_file.exists() else {}
    kev = json.loads(kev_file.read_text()) if kev_file.exists() else {}
    return {"cve": cve, "kev": set(kev.get("cves", []))}


def _enrich_services(services: list[dict], cache: dict) -> list[dict]:
    for svc in services:
        if svc.get("service") == "http":
            svc.setdefault("cves", ["CVE-0001"])
        details = []
        for cve in svc.get("cves", []):
            meta = cache["cve"].get(cve, {})
            details.append({"id": cve, "kev": cve in cache["kev"], **meta})
        if details:
            svc["cves"] = details
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
        services: list[dict] = []
        if profile in {"version", "full"}:
            services.append({"port": 80, "service": "http", "nmap": "sample"})
        if profile == "full":
            services.append({"port": 443, "service": "https", "nmap": "sample"})
        cache = _load_cache()
        services = _enrich_services(services, cache)
        findings = []
        if profile == "full":
            findings.append({"url": f"http://{target}", "issue": "xss"})
        cache_counts = {"cve": len(cache["cve"]), "kev": len(cache["kev"])}
        inventory = {"hosts": [target], "services": services, "findings": findings, "cache": cache_counts}
        data = {"target": target, "profile": profile, "inventory": inventory}
        path = write_result("recon", data, run_dir=out_dir)
        return json.dumps({"ok": True, "result": path})
    except Deny as e:
        return json.dumps({"ok": False, "deny": str(e)})
