import json
from pathlib import Path
from skills.cyber_common import write_result


def tool(payload: str) -> str:
    """Placeholder network forensics processing.
    Input JSON: {"pcap":"capture.pcap","out_dir":"..."}
    """
    args = json.loads(payload or "{}")
    pcap = args.get("pcap", "")
    out_dir = args.get("out_dir")
    pcap_path = Path(pcap)
    flows = pcap_path.stat().st_size if pcap_path.exists() else 0
    data = {"pcap": pcap, "flows": flows, "alerts": []}
    path = write_result("netforensics", data, run_dir=out_dir)
    return json.dumps({"ok": True, "result": path})
