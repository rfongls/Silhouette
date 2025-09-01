import json
from skills.cyber_common import require_auth_and_scope, write_result, Deny


def tool(payload: str) -> str:
    """Perform placeholder recon on the target.

    Input JSON: {"target":"example.com","scope_file":"scope.txt","out_dir":"out/security/..."}
    """
    args = json.loads(payload or "{}")
    target = args.get("target", "")
    scope_file = args.get("scope_file", "scope.txt")
    out_dir = args.get("out_dir")
    try:
        require_auth_and_scope(scope_file, target)
        inventory = {"hosts": [target], "services": []}
        path = write_result(
            "recon", {"target": target, "inventory": inventory}, run_dir=out_dir
        )
        return json.dumps({"ok": True, "result": path})
    except Deny as e:
        return json.dumps({"ok": False, "deny": str(e)})
