import json
import shlex
from pathlib import Path
from silhouette_core.skills.cyber_common import run_docker, write_result


def tool(payload: str) -> str:
    """
    Input: {"target":"alpine:3.19"}   OR   {"dir":"./"}
    Output: {"ok":true,"result":"/path/to/json"}
    """
    args = json.loads(payload or "{}")
    image = args.get("target")
    directory = args.get("dir")
    if image:
        cmd = f"trivy image --quiet --format json {shlex.quote(image)}"
        rc, out, err = run_docker("aquasec/trivy:latest", cmd)
    else:
        cmd = "trivy fs --quiet --format json /wrk"
        mounts = [f"{Path.cwd().resolve()}:/wrk"]
        rc, out, err = run_docker("aquasec/trivy:latest", cmd, mounts=mounts)
    if rc != 0:
        return json.dumps({"ok": False, "stderr": err})
    path = write_result("trivy", {"stdout": out, "stderr": err})
    return json.dumps({"ok": True, "result": path})
