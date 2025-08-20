import json
import os
import re
import shutil
import subprocess
from skills.cyber_common import write_result


def _check(cmd):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return {"rc": p.returncode, "out": p.stdout.strip(), "err": p.stderr.strip()}
    except Exception as e:
        return {"rc": 9, "err": str(e), "out": ""}


def tool(payload: str = "") -> str:
    """
    Runs a few simple CIS-like checks (Linux):
    - SSH root login disabled
    - Password max age policy
    - World-writable files in /etc
    """
    results = {}
    sshd = "/etc/ssh/sshd_config"
    if os.path.exists(sshd):
        txt = open(sshd).read()
        m = re.search(r"^\s*PermitRootLogin\s+(\w+)", txt, flags=re.MULTILINE)
        results["ssh_permit_root_login"] = (m.group(1).lower() if m else "missing")
    else:
        results["ssh_permit_root_login"] = "not_found"

    chage = shutil.which("chage")
    if chage:
        q = _check("chage -l root")
        results["passwd_root_maxdays"] = q["out"]
    else:
        results["passwd_root_maxdays"] = "chage_not_available"

    q2 = _check("find /etc -xdev -type f -perm -0002 2>/dev/null | head -n 20")
    results["world_writable_etc_sample"] = q2["out"].splitlines()

    path = write_result("cis_audit", {"results": results})
    return json.dumps({"ok": True, "result": path})
