import json
import struct
from collections import Counter
from ipaddress import ip_address
from pathlib import Path
from skills.cyber_common import write_result


def _analyze_pcap(pcap_path: Path) -> tuple[int, Counter[tuple[bytes, bytes, int, int, int]]]:
    """Return packet count and flow index from a PCAP file.

    Only handles Ethernet/IPv4/TCP-UDP packets. Counts a *flow* as the
    5-tuple ``(src_ip, dst_ip, src_port, dst_port, protocol)``.
    """
    if not pcap_path.exists():
        return 0, Counter()
    flows: Counter[tuple[bytes, bytes, int, int, int]] = Counter()
    packets = 0
    with pcap_path.open("rb") as fh:
        header = fh.read(24)
        if len(header) < 24:
            return 0, Counter()
        magic = header[:4]
        endian = "<" if magic == b"\xd4\xc3\xb2\xa1" else ">"
        unpack_hdr = endian + "IIII"
        while True:
            pkt_hdr = fh.read(16)
            if len(pkt_hdr) < 16:
                break
            _ts_sec, _ts_usec, incl_len, _orig_len = struct.unpack(unpack_hdr, pkt_hdr)
            payload = fh.read(incl_len)
            if len(payload) < incl_len:
                break
            packets += 1
            if len(payload) < 34:  # insufficient for Ethernet+IPv4
                continue
            eth_type = struct.unpack("!H", payload[12:14])[0]
            if eth_type != 0x0800:
                continue  # not IPv4
            ihl = (payload[14] & 0x0F) * 4
            proto = payload[23]
            if len(payload) < 14 + ihl + 4:
                continue
            src_ip = payload[26:30]
            dst_ip = payload[30:34]
            if proto in (6, 17) and len(payload) >= 14 + ihl + 4:
                src_port, dst_port = struct.unpack("!HH", payload[14 + ihl:14 + ihl + 4])
            else:
                src_port = dst_port = 0
            flows[(src_ip, dst_ip, src_port, dst_port, proto)] += 1
    return packets, flows


def _extract_artifacts(pcap_path: Path, run_dir: Path) -> list[str]:
    if not pcap_path.exists():
        return []
    artifact = run_dir / f"{pcap_path.stem}_http.txt"
    artifact.write_text("placeholder artifact")
    return [str(artifact)]


def tool(payload: str) -> str:
    """Network forensics processing.
    Input JSON: {"pcap":"capture.pcap","out_dir":"..."}
    """
    args = json.loads(payload or "{}")
    pcap = args.get("pcap", "")
    capture = args.get("capture")
    ssl_keylog = args.get("ssl_keylog")
    out_dir = args.get("out_dir")
    pcap_path = Path(capture or pcap)
    if capture:
        pcap_path.write_bytes(b"")
    packets, flows = _analyze_pcap(pcap_path)
    index = [
        {
            "src": str(ip_address(src)),
            "dst": str(ip_address(dst)),
            "src_port": sp,
            "dst_port": dp,
            "proto": proto,
            "count": cnt,
        }
        for (src, dst, sp, dp, proto), cnt in flows.items()
    ]
    alerts = []
    for (src, dst, sp, dp, proto), cnt in flows.items():
        if dp == 23:
            alerts.append({"dst": str(ip_address(dst)), "port": dp, "reason": "telnet"})
    data = {
        "pcap": pcap,
        "packets": packets,
        "flows": len(flows),
        "index": index,
        "alerts": alerts,
        "tls_keys": bool(ssl_keylog and Path(ssl_keylog).exists()),
    }
    path = write_result("netforensics", data, run_dir=out_dir)
    run_dir = Path(path).parent
    artifacts = _extract_artifacts(pcap_path, run_dir)
    if artifacts:
        triage = []
        for art in artifacts:
            txt = Path(art).read_text()
            if "malware" in txt:
                triage.append({"path": art, "rule": "malware"})
        data["artifacts"] = artifacts
        data["triage"] = triage
        Path(path).write_text(json.dumps(data, indent=2))
    return json.dumps({"ok": True, "result": path})
