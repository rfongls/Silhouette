#!/usr/bin/env python
"""
HL7 batch parser + basic QA report

- Accepts a single HL7 file OR a directory (recurses .hl7 files)
- Normalizes line endings to \r (HL7 ER7)
- Parses with hl7apy
- Emits console summary + CSV report (hl7_qa_report.csv) alongside the input root

Install deps:
  py -m pip install hl7apy
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from hl7apy.exceptions import HL7apyException
    from hl7apy.parser import parse_message
except ModuleNotFoundError:
    print("hl7apy is not installed. Install with: py -m pip install hl7apy")
    sys.exit(1)


def normalize_hl7_text(data: bytes) -> str:
    txt = data.decode("latin-1", errors="ignore")
    txt = txt.replace("\r\n", "\r").replace("\n", "\r").replace("\r\r", "\r")
    return txt


def first_segment(msg, name: str):
    for s in msg.children:
        if getattr(s, "name", "") == name:
            return s
    return None


def collect_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    return sorted([p for p in target.rglob("*.hl7") if p.is_file()])


def segment_counts(msg) -> dict[str, int]:
    return dict(Counter(s.name for s in msg.children if hasattr(s, "name")))


def safe_get(component, attr: str, default: str = "") -> str:
    try:
        return getattr(component, attr).to_er7() if hasattr(component, attr) else default
    except Exception:
        return default


def qa_one_file(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "file": str(path),
        "status": "ok",
        "error": "",
        "issues": [],
        "msh_3": "",
        "msh_4": "",
        "pid_3": "",
        "seg_counts": {},
    }

    try:
        data = path.read_bytes()
    except Exception as e:
        result["status"] = "read_error"
        result["error"] = f"read failed: {e}"
        return result

    txt = normalize_hl7_text(data)

    try:
        msg = parse_message(txt, find_groups=False)
    except HL7apyException as e:
        result["status"] = "parse_error"
        result["error"] = str(e)
        return result
    except Exception as e:
        result["status"] = "parse_error"
        result["error"] = f"unexpected parse error: {e}"
        return result

    msh = first_segment(msg, "MSH")
    pid = first_segment(msg, "PID")
    obr = first_segment(msg, "OBR")
    obx = first_segment(msg, "OBX")

    if not msh:
        result["issues"].append("MSH missing")
    if not pid:
        result["issues"].append("PID missing")
    if not obr:
        result["issues"].append("OBR missing (order)")
    if not obx:
        result["issues"].append("OBX missing (observations)")

    if msh:
        result["msh_3"] = safe_get(msh, "msh_3", "<MSH-3 missing>")
        result["msh_4"] = safe_get(msh, "msh_4", "<MSH-4 missing>")
    if pid:
        result["pid_3"] = safe_get(pid, "pid_3", "<PID-3 missing>")

    result["seg_counts"] = segment_counts(msg)
    return result


def write_csv(out_path: Path, rows: list[dict[str, Any]]) -> Path:
    for r in rows:
        r["issues_joined"] = "; ".join(r.get("issues", [])) if r.get("issues") else ""
        r["seg_counts_str"] = ", ".join(f"{k}:{v}" for k, v in (r.get("seg_counts") or {}).items())

    fieldnames = [
        "file",
        "status",
        "error",
        "issues_joined",
        "msh_3",
        "msh_4",
        "pid_3",
        "seg_counts_str",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})
    return out_path


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage:")
        print("  py tools\\hl7_qa.py <path_to_hl7_file_or_folder>")
        return 2

    target = Path(argv[1])
    files = collect_files(target)
    if not files:
        print(f"No .hl7 files found under: {target}")
        return 3

    print(f"Found {len(files)} HL7 file(s). Processing…\n")
    results: list[dict[str, Any]] = []
    ok = err = 0

    for p in files:
        r = qa_one_file(p)
        results.append(r)
        status = r["status"]
        issues = r.get("issues") or []
        if status == "ok":
            ok += 1
        else:
            err += 1

        print(f"[{status}] {p.name}")
        if r.get("error"):
            print(f"  error: {r['error']}")
        if issues:
            print(f"  issues: {', '.join(issues)}")
        if r.get("msh_3") or r.get("msh_4"):
            print(f"  MSH-3: {r.get('msh_3','')}")
            print(f"  MSH-4: {r.get('msh_4','')}")
        if r.get("pid_3"):
            print(f"  PID-3: {r['pid_3']}")
        if r.get("seg_counts"):
            print(f"  seg_counts: {r['seg_counts']}")
        print("")

    root_for_output = target if target.is_dir() else target.parent
    csv_path = root_for_output / "hl7_qa_report.csv"
    write_csv(csv_path, results)

    print(f"Done. OK: {ok}  Errors: {err}")
    print(f"Report: {csv_path}")
    return 0 if err == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
