import json
import shlex
from pathlib import Path
from silhouette_core.skills.cyber_common import require_auth_and_scope, run_docker, write_result, Deny


def tool(payload: str) -> str:
    """
    Input: {"url":"https://site.example","scope_file":"scope.txt","time":"60"}
    Runs zap-baseline.py with passive checks; returns JSON report path.
    """
    args = json.loads(payload or "{}")
    url = args.get("url", "")
    scope_file = args.get("scope_file", "scope.txt")
    minutes = int(args.get("time", "2"))
    try:
        require_auth_and_scope(scope_file, url)
        cmd = f"zap-baseline.py -t {shlex.quote(url)} -m {minutes} -J /zap/wrk/report.json -x /zap/wrk/report.xml -I"
        mounts = [f"{Path.cwd().resolve()}/artifacts/cyber:/zap/wrk"]
        rc, out, err = run_docker("owasp/zap2docker-stable", cmd, mounts=mounts, network_host=True, timeout=minutes*120)
        path = write_result("zap_baseline", {"stdout": out, "stderr": err})
        if rc != 0:
            return json.dumps({"ok": False, "stderr": err, "report": path})
        return json.dumps({"ok": True, "report": path, "stderr": err})
    except Deny as e:
        return json.dumps({"ok": False, "deny": str(e)})
