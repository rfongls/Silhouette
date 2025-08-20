import ipaddress
import json
import os
import pathlib
import re
import subprocess
import shlex
import time

ART = pathlib.Path("artifacts/cyber")
ART.mkdir(parents=True, exist_ok=True)

class Deny(Exception):
    pass

def load_scope(scope_file: str):
    p = pathlib.Path(scope_file)
    if not p.exists():
        raise Deny(f"Scope file not found: {scope_file}")
    lines = [l.strip() for l in p.read_text().splitlines() if l.strip() and not l.strip().startswith("#")]
    nets, hosts, urls = [], [], []
    for l in lines:
        if re.match(r"^https?://", l):
            urls.append(l)
        else:
            try:
                if "/" in l:
                    nets.append(ipaddress.ip_network(l, strict=False))
                else:
                    hosts.append(ipaddress.ip_address(l))
            except ValueError:
                hosts.append(l)
    return {"nets": nets, "hosts": hosts, "urls": urls, "raw": lines}

def target_in_scope(target: str, scope):
    if re.match(r"^https?://", target):
        return any(target.startswith(u) for u in scope["urls"])
    try:
        ip = ipaddress.ip_address(target)
        if any(ip in n for n in scope["nets"]):
            return True
        return any(str(ip) == str(h) for h in scope["hosts"])
    except ValueError:
        return target in [str(h) for h in scope["hosts"]]

def require_auth_and_scope(scope_file: str, target: str):
    if os.environ.get("SILHOUETTE_PEN_TEST_OK") != "1":
        raise Deny("Pen-test not authorized: set SILHOUETTE_PEN_TEST_OK=1")
    scope = load_scope(scope_file)
    if not target_in_scope(target, scope):
        raise Deny(f"Target {target} not in scope. See {scope_file}")
    return scope

def run_docker(image: str, cmd: str, mounts=None, network_host=False, timeout=600):
    mounts = mounts or []
    base = ["docker", "run", "--rm"]
    if network_host:
        base += ["--network", "host"]
    for m in mounts:
        base += ["-v", m]
    full = base + [image, "bash", "-lc", cmd]
    res = subprocess.run(full, capture_output=True, text=True, timeout=timeout)
    return res.returncode, res.stdout, res.stderr

def write_result(name: str, payload: dict):
    ts = int(time.time())
    out = ART / f"{name}_{ts}.json"
    out.write_text(json.dumps(payload, indent=2))
    return str(out)
