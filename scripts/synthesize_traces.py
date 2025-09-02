#!/usr/bin/env python
import argparse
import json
import os
import pathlib
import time
from security.redaction import DEFAULT_REDACTOR as _redactor

ART = pathlib.Path("artifacts")
FLYWHEEL = pathlib.Path("training_data/flywheel")

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
    return _redactor.redact_text(s)

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
            content = _redact_text(_read_file(p))
            out.append({"path": str(p.relative_to(root)), "content": content})
    return out

def _append_trace(path: pathlib.Path, record: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def synthesize_one_report(rep):
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
        lane = case.get("lane", "misc")
        lane_out = FLYWHEEL / lane / "runtime.jsonl"
        _append_trace(lane_out, record)
    return total

def main():
    argparse.ArgumentParser().parse_args()
    n = 0
    for p in _iter_runtime_reports():
        rep = _load_json(p)
        n += synthesize_one_report(rep)
    print(f"Wrote {n} traces -> {FLYWHEEL}")

if __name__ == "__main__":
    main()
