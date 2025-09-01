import json
from skills.cyber_common import write_result


def tool(payload: str) -> str:
    """Placeholder network forensics processing.

    Input JSON: {"pcap":"capture.pcap","out_dir":"..."}
    """
    args = json.loads(payload or "{}")
    pcap = args.get("pcap", "")
    out_dir = args.get("out_dir")
    data = {"pcap": pcap, "flows": 0, "alerts": []}
    path = write_result("netforensics", data, run_dir=out_dir)
    return json.dumps({"ok": True, "result": path})
