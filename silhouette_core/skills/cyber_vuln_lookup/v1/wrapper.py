import json
import pathlib

CACHE = pathlib.Path("docs/cyber/cve_cache.json")


def tool(cve_id: str) -> str:
    """
    Input: "CVE-2025-12345"
    Output: {"id":..,"summary":..,"cvss":..,"refs":[...]} or error
    """
    if not CACHE.exists():
        return json.dumps({"error": "no_cache", "path": str(CACHE)})
    data = json.loads(CACHE.read_text())
    ent = data.get(cve_id)
    if not ent:
        return json.dumps({"ok": False, "not_found": cve_id})
    return json.dumps({"ok": True, "cve": ent})
