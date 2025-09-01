import json
import shlex
import xml.etree.ElementTree as ET
from silhouette_core.skills.cyber_common import (
    require_auth_and_scope,
    run_docker,
    write_result,
    Deny,
)


def _parse_nmap_xml(xml_text: str):
    root = ET.fromstring(xml_text)
    hosts = []
    for h in root.findall(".//host"):
        addr_el = h.find("address")
        addr = addr_el.attrib.get("addr") if addr_el is not None else None
        ports = []
        for p in h.findall(".//port"):
            ports.append(
                {
                    "port": p.attrib.get("portid"),
                    "proto": p.attrib.get("protocol"),
                    "state": (p.find("state") or {}).attrib.get("state", ""),
                    "service": (p.find("service") or {}).attrib.get("name", ""),
                }
            )
        hosts.append({"address": addr, "ports": ports})
    return {"hosts": hosts}


def tool(payload: str) -> str:
    """
    Input JSON: {"target":"192.168.1.10","scope_file":"scope.txt","timing":"T3"}
    Runs nmap top-1000 TCP in container; outputs JSON result path.
    """
    args = json.loads(payload or "{}")
    target = args.get("target", "")
    scope_file = args.get("scope_file", "scope.txt")
    timing = args.get("timing", "T3")
    try:
        require_auth_and_scope(scope_file, target)
        cmd = f"nmap -{timing} -sS -Pn --top-ports 1000 -oX - {shlex.quote(target)}"
        rc, out, err = run_docker("instrumentisto/nmap:latest", cmd, network_host=True)
        if rc != 0:
            return json.dumps({"error": "nmap_failed", "stderr": err})
        data = _parse_nmap_xml(out)
        path = write_result("nmap", {"target": target, "data": data, "stderr": err})
        return json.dumps({"ok": True, "result": path})
    except Deny as e:
        return json.dumps({"ok": False, "deny": str(e)})
