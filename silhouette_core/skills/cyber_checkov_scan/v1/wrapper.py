import json
from pathlib import Path
from silhouette_core.skills.cyber_common import run_docker, write_result


def tool(payload: str) -> str:
    """
    Input: {"dir":"./infra"}
    """
    args = json.loads(payload or "{}")
    directory = args.get("dir", "./")
    mounts = [f"{Path.cwd().resolve()}:/wrk"]
    rc, out, err = run_docker("bridgecrew/checkov:latest", f"checkov -d /wrk/{directory}", mounts=mounts)
    if rc not in (0, 2):
        return json.dumps({"ok": False, "stderr": err, "stdout": out})
    path = write_result("checkov", {"stdout": out, "stderr": err})
    return json.dumps({"ok": True, "result": path})
