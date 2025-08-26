#!/usr/bin/env python
from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Tuple
import sys, csv, json, argparse, warnings, re
from collections import Counter
from datetime import datetime

try:
    from hl7apy.parser import parse_message
    from hl7apy.exceptions import HL7apyException
except ModuleNotFoundError:
    print("hl7apy is not installed. Install with: py -m pip install hl7apy")
    sys.exit(1)

# ---------- IO & normalization ----------

def normalize_hl7_text(data: bytes) -> str:
    """Decode bytes liberally and normalize all line endings to HL7's \\r."""
    txt = data.decode("latin-1", errors="ignore")
    # Strip MLLP framing if present
    txt = txt.replace("\x0b", "").replace("\x1c\r", "")
    # Normalize newlines to \r
    txt = txt.replace("\r\n", "\r").replace("\n", "\r").replace("\r\r", "\r")
    return txt

def strip_batch_envelopes(txt: str) -> str:
    """Remove FHS/BHS/BTS/FTS envelope lines; keep inner MSH... segments."""
    return re.sub(r'^(?:FHS|BHS|BTS|FTS)\|.*\r?', "", txt, flags=re.MULTILINE)

def split_messages(txt: str) -> List[str]:
    """
    Split a batched HL7 text into individual ER7 messages.
    Heuristic: messages start at lines beginning with 'MSH|'.
    """
    if not txt:
        return []
    txt = strip_batch_envelopes(txt)
    if not txt.endswith("\r"):
        txt += "\r"
    parts = re.split(r'(?=^MSH\|)', txt, flags=re.MULTILINE)
    msgs = [p.strip() for p in parts if p.strip()]
    msgs = [m if m.endswith("\r") else (m + "\r") for m in msgs]
    return msgs

# ---------- helpers ----------

def first_segment(msg, name: str):
    for s in msg.children:
        if getattr(s, "name", "") == name:
            return s
    return None

def segment_counts(msg) -> Dict[str, int]:
    return dict(Counter(s.name for s in msg.children if hasattr(s, "name")))

def safe_get_er7(component, attr: str, default: str = "") -> str:
    try:
        return getattr(component, attr).to_er7() if hasattr(component, attr) else default
    except Exception:
        return default

def get_msg_type_and_event(msh) -> Tuple[str, str]:
    raw = safe_get_er7(msh, "msh_9", "")
    parts = raw.split("^") if raw else []
    return (parts[0] if len(parts) >= 1 else "",
            parts[1] if len(parts) >= 2 else "")

def count_segments(msg, name: str) -> int:
    return sum(1 for s in msg.children if getattr(s, "name", "") == name)

# ---------- strict timestamp checks (YYYYMMDD or YYYYMMDDHHMMSS) ----------

def ts_is_valid_strict(value: str) -> bool:
    """
    Accept only:
      - YYYYMMDD
      - YYYYMMDDHHMMSS
    Allow a literal 'T' between date and time.
    """
    if not value:
        return False
    v = value.strip().replace("T", "")
    if not v.isdigit():
        return False
    try:
        if len(v) == 8:
            datetime.strptime(v, "%Y%m%d")
            return True
        if len(v) == 14:
            datetime.strptime(v, "%Y%m%d%H%M%S")
            return True
        return False
    except ValueError:
        return False

def ts_normalize_strict(value: str) -> str:
    """
    Return ISO-like normalized string for valid strict timestamps:
      - YYYY-MM-DD
      - YYYY-MM-DDTHH:MM:SS
    Else ''.
    """
    if not value:
        return ""
    v = value.strip().replace("T", "")
    if not v.isdigit():
        return ""
    try:
        if len(v) == 8:
            dt = datetime.strptime(v, "%Y%m%d")
            return dt.strftime("%Y-%m-%d")
        if len(v) == 14:
            dt = datetime.strptime(v, "%Y%m%d%H%M%S")
            return dt.strftime("%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return ""
    return ""

# ---------- rules ----------

def qa_rules_by_type(msg, msh, pid) -> List[str]:
    """
    Baseline rules per message type (MSH-9):
      ORU: require OBR and >=1 OBX
      ORM/OML: require OBR
      MDM: require TXA
      RDE: require RXE
      VXU: require RXA
      ADT: no OBR/OBX requirement (PV1 recommended but not enforced here)
      All: MSH required; PID required
    """
    issues: List[str] = []
    if not msh:
        issues.append("MSH missing")
        return issues
    if not pid:
        issues.append("PID missing")

    mt, _ = get_msg_type_and_event(msh)
    mt = (mt or "").upper()

    obr_n = count_segments(msg, "OBR")
    obx_n = count_segments(msg, "OBX")
    txa_n = count_segments(msg, "TXA")
    rxe_n = count_segments(msg, "RXE")
    rxa_n = count_segments(msg, "RXA")

    if mt == "ORU":
        if obr_n == 0:
            issues.append("OBR missing (required for ORU)")
        if obx_n == 0:
            issues.append("OBX missing (required for ORU results)")
    elif mt in {"ORM", "OML"}:
        if obr_n == 0:
            issues.append("OBR missing (required for ORM/OML)")
    elif mt == "MDM":
        if txa_n == 0:
            issues.append("TXA missing (required for MDM)")
    elif mt == "RDE":
        if rxe_n == 0:
            issues.append("RXE missing (required for RDE)")
    elif mt == "VXU":
        if rxa_n == 0:
            issues.append("RXA missing (required for VXU)")
    return issues

# ---------- TS field scanning ----------

def collect_ts_field_issues_and_norms(msg) -> Tuple[List[str], Dict[str, str]]:
    """
    Scan common TS/DTM fields; return (issues, norms) where norms contains normalized
    values for certain well-known fields (for CSV convenience).
    """
    issues: List[str] = []
    norms: Dict[str, str] = {}

    def chk(seg, field_name, label, norm_key: str | None = None):
        if seg:
            val = safe_get_er7(seg, field_name, "")
            if val:
                if not ts_is_valid_strict(val):
                    issues.append(f"{label} invalid TS: {val}")
                else:
                    if norm_key:
                        norms[norm_key] = ts_normalize_strict(val)

    msh = first_segment(msg, "MSH")
    pid = first_segment(msg, "PID")

    # MSH-7 (Date/Time of Message)
    chk(msh, "msh_7", "MSH-7 (Date/Time of Message)", norm_key="msh7_norm")

    # PID-7 (DOB)
    chk(pid, "pid_7", "PID-7 (Date/Time of Birth)", norm_key="pid7_norm")

    # OBR date fields
    for seg in (s for s in msg.children if getattr(s, "name", "") == "OBR"):
        for f, label in [("obr_6", "OBR-6 (Requested Date/Time)"),
                         ("obr_7", "OBR-7 (Observation Date/Time)"),
                         ("obr_14","OBR-14 (Specimen Received Date/Time)"),
                         ("obr_22","OBR-22 (Results Rpt/Status Chg Date/Time)")]:
            val = safe_get_er7(seg, f, "")
            if val and not ts_is_valid_strict(val):
                issues.append(f"{label} invalid TS: {val}")

    # OBX-14 (Date/Time of Observation)
    for seg in (s for s in msg.children if getattr(s, "name", "") == "OBX"):
        val = safe_get_er7(seg, "obx_14", "")
        if val and not ts_is_valid_strict(val):
            issues.append(f"OBX-14 (Date/Time of Observation) invalid TS: {val}")

    # RXA dates (VXU)
    for seg in (s for s in msg.children if getattr(s, "name", "") == "RXA"):
        for f, label in [("rxa_3","RXA-3 (Date/Time Start of Admin)"),
                         ("rxa_4","RXA-4 (Date/Time End of Admin)")]:
            val = safe_get_er7(seg, f, "")
            if val and not ts_is_valid_strict(val):
                issues.append(f"{label} invalid TS: {val}")

    # TXA-6 (MDM)
    for seg in (s for s in msg.children if getattr(s, "name", "") == "TXA"):
        val = safe_get_er7(seg, "txa_6", "")
        if val and not ts_is_valid_strict(val):
            issues.append(f"TXA-6 (Transcription Date/Time) invalid TS: {val}")

    return issues, norms

# ---------- per-message QA ----------

def qa_one_message(raw_msg: str, fail_on_dtm: bool = False, quiet_parse: bool = False) -> Dict[str, Any]:
    res: Dict[str, Any] = {
        "status": "ok",
        "error": "",
        "issues": [],
        "msg_type": "",
        "msg_event": "",
        "msh_3": "",
        "msh_4": "",
        "msh_10": "",
        "pid_3": "",
        "msh7_norm": "",
        "pid7_norm": "",
        "obr_count": 0,
        "obx_count": 0,
        "seg_counts": {},
        "dtm_issues": [],
    }
    if quiet_parse:
        warnings.filterwarnings("ignore")

    try:
        msg = parse_message(raw_msg, find_groups=False)
    except HL7apyException as e:
        res["status"] = "parse_error"
        res["error"] = str(e)
        return res
    except Exception as e:
        res["status"] = "parse_error"
        res["error"] = f"unexpected parse error: {e}"
        return res

    msh = first_segment(msg, "MSH")
    pid = first_segment(msg, "PID")

    if msh:
        res["msh_3"]  = safe_get_er7(msh, "msh_3", "<MSH-3 missing>")
        res["msh_4"]  = safe_get_er7(msh, "msh_4", "<MSH-4 missing>")
        res["msh_10"] = safe_get_er7(msh, "msh_10", "<MSH-10 missing>")
        mt, me = get_msg_type_and_event(msh)
        res["msg_type"], res["msg_event"] = mt, me
    if pid:
        res["pid_3"] = safe_get_er7(pid, "pid_3", "<PID-3 missing>")

    res["seg_counts"] = segment_counts(msg)
    res["obr_count"] = res["seg_counts"].get("OBR", 0)
    res["obx_count"] = res["seg_counts"].get("OBX", 0)

    # Rules
    res["issues"] = qa_rules_by_type(msg, msh, pid)

    # Timestamp issues + normalized values
    dtm_issues, norms = collect_ts_field_issues_and_norms(msg)
    res["dtm_issues"] = dtm_issues
    res["msh7_norm"] = norms.get("msh7_norm", "")
    res["pid7_norm"] = norms.get("pid7_norm", "")

    if fail_on_dtm and dtm_issues and res["status"] == "ok":
        res["status"] = "value_error"

    return res

# ---------- per-file driver ----------

def qa_one_file(path: Path, fail_on_dtm: bool, quiet_parse: bool) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    rows: List[Dict[str, Any]] = []
    summary = {"total": 0, "ok": 0, "errors": 0}

    try:
        data = path.read_bytes()
    except Exception as e:
        rows.append({
            "file": str(path), "message_index": "",
            "status": "read_error", "error": f"read failed: {e}",
        })
        summary["total"] += 1
        summary["errors"] += 1
        return rows, summary

    txt = normalize_hl7_text(data)
    messages = split_messages(txt) or [txt]

    for i, raw_msg in enumerate(messages, start=1):
        res = qa_one_message(raw_msg, fail_on_dtm=fail_on_dtm, quiet_parse=quiet_parse)
        res["file"] = str(path)
        res["message_index"] = i
        rows.append(res)
        summary["total"] += 1
        if res["status"] == "ok":
            summary["ok"] += 1
        else:
            summary["errors"] += 1

    return rows, summary

# ---------- CSV & CLI ----------

CSV_FIELDS = [
    "file", "message_index",
    "status", "error",
    "msg_type", "msg_event",
    "issues_joined",
    "msh_3", "msh_4", "msh_10", "pid_3",
    "msh7_norm", "pid7_norm",
    "obr_count", "obx_count",
    "seg_counts_str",
    "dtm_issues_joined",
]

def write_csv(out_path: Path, rows: List[Dict[str, Any]]) -> Path:
    for r in rows:
        r["issues_joined"] = "; ".join(r.get("issues", [])) if r.get("issues") else ""
        r["seg_counts_str"] = ", ".join(f"{k}:{v}" for k, v in (r.get("seg_counts") or {}).items())
        r["dtm_issues_joined"] = "; ".join(r.get("dtm_issues", [])) if r.get("dtm_issues") else ""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in CSV_FIELDS})
    return out_path

def collect_files(target: Path) -> List[Path]:
    if target.is_file():
        return [target]
    return sorted([p for p in target.rglob("*.hl7") if p.is_file()])

def run_cli(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="HL7 batch parser + QA (message-type aware, per-message, strict TS)")
    ap.add_argument("path", help="HL7 file or directory")
    ap.add_argument("--report", help="CSV output path (default: alongside input)")
    ap.add_argument("--json", dest="as_json", action="store_true", help="Emit results as JSON to stdout")
    ap.add_argument("--fail-on-dtm", action="store_true", help="Mark message as value_error if any timestamp is invalid")
    ap.add_argument("--quiet-parse", action="store_true", help="Suppress parser warnings/noise")
    ap.add_argument("--max-print", type=int, default=10, help="Max messages to print per file (console summary)")
    ap.add_argument("--verbose", action="store_true", help="Print every message (overrides --max-print)")
    args = ap.parse_args(argv[1:])

    target = Path(args.path)
    files = collect_files(target)
    if not files:
        print(f"No .hl7 files found under: {target}")
        return 3

    all_rows: List[Dict[str, Any]] = []
    grand = {"files": 0, "messages": 0, "ok": 0, "errors": 0}

    for f in files:
        rows, summary = qa_one_file(f, fail_on_dtm=args.fail_on_dtm, quiet_parse=args.quiet_parse)
        all_rows.extend(rows)
        grand["files"] += 1
        grand["messages"] += summary["total"]
        grand["ok"] += summary["ok"]
        grand["errors"] += summary["errors"]

        print(f"[file] {f.name} → messages: {summary['total']}  ok: {summary['ok']}  errors: {summary['errors']}")
        limit = len(rows) if args.verbose else min(args.max_print, len(rows))
        for r in rows[:limit]:
            print(f"  [{r['status']}] msg#{r['message_index']} type={r.get('msg_type','')}^{r.get('msg_event','')}".rstrip("^"))
            if r.get("error"):
                print(f"    error: {r['error']}")
            if r.get("issues"):
                print(f"    issues: {', '.join(r['issues'])}")
            if r.get("dtm_issues"):
                print(f"    dtm_issues: {', '.join(r['dtm_issues'])}")
            print(f"    MSH-10: {r.get('msh_10','')}")
            print(f"    PID-3:  {r.get('pid_3','')}")
            print(f"    counts: OBR={r.get('obr_count',0)} OBX={r.get('obx_count',0)}")

    # CSV output
    if args.report:
        csv_path = Path(args.report)
    else:
        root_for_output = target if target.is_dir() else target.parent
        csv_path = root_for_output / "hl7_qa_report.csv"
    write_csv(csv_path, all_rows)

    if args.as_json:
        print(json.dumps(all_rows, ensure_ascii=False))

    print(f"\n[total] files: {grand['files']}  messages: {grand['messages']}  ok: {grand['ok']}  errors: {grand['errors']}")
    print(f"[report] {csv_path}")
    return 0 if grand["errors"] == 0 else 1

def main(argv: List[str]) -> int:
    return run_cli(argv)

if __name__ == "__main__":
    sys.exit(main(sys.argv))
