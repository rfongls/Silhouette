#!/usr/bin/env python
import argparse
import json
import os
import pathlib
import re
import time

ART = pathlib.Path("artifacts")
TRACES = ART / "traces"
DEFAULT_OUT = TRACES / "runtime_kd.jsonl"

def _iter_runtime_reports():
    for p in ART.glob("*.build_eval_report.json"):
        yield p
    p = ART / "build_eval_report.json"
    if p.exists():
        yield p

def _load_json(p: pathlib.Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def _redact_text(s: str) -> str:
    if not s:
        return s
    s = re.sub(r"(?i)api[_-]?key[:=]\s*[\w\-]+", "API_KEY:REDACTED", s)
    s = re.sub(r"https?://[^\s\"']+", "URL:REDACTED", s)
    return s

def _read_file(path: pathlib.Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""

def _collect_files(workdir: str, step_logs):
    root = pathlib.Path(workdir)
    out = []
    exts = {".py", ".kt", ".java", ".cs", ".html", ".htm", ".xml", ".kts", ".gradle", ".md", ".yml", ".yaml", ".txt"}
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts and p.stat().st_size <= 200_000:
            out.append({"path": str(p.relative_to(root)), "content": _read_file(p)})
    return out

def synthesize_one_report(rep, out_f):
    if not rep or rep.get("skipped"):
        return 0
    suite = rep.get("suite", "")
    total = 0
    for case in rep.get("cases", []):
        if not case.get("ok"):
            continue
        total += 1
        cid = case.get("id", "")
        workdir = case.get("workdir", "")
        steps = case.get("steps", [])
        stdout_all = "\n".join([s.get("stdout", "") for s in steps])
        files = _collect_files(workdir, steps) if workdir else []
        instruction = f"[runtime:{suite}/{cid}] Generate project files that compile and tests pass."
        record = {
            "task_id": cid,
            "suite": suite,
            "timestamp": int(time.time()),
            "instruction": _redact_text(instruction),
            "input": "",
            "files": files,
            "commands": [s.get("cmd", "") for s in steps],
            "stdout": _redact_text(stdout_all),
            "teacher_output": "OK",
            "teacher_meta": {"rc": case.get("rc", 0)},
            "license": os.environ.get("TRACE_LICENSE", "internal-training-only"),
            "redactions": ["secrets", "urls"],
            "tags": ["runtime"] + suite.split("_"),
        }
        out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return total

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    os.makedirs(TRACES, exist_ok=True)
    n = 0
    with open(args.out, "w", encoding="utf-8") as f:
        for p in _iter_runtime_reports():
            rep = _load_json(p)
            n += synthesize_one_report(rep, f)
    print(f"Wrote {n} traces -> {args.out}")

if __name__ == "__main__":
    main()
