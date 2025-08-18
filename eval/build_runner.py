import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import pathlib
import yaml
from typing import Dict, Any, List
from silhouette_core.agent_loop import Agent
from silhouette_core.response_engine import generate_text as _gen

OFFLINE_TAG = "[offline-stub]"


def _is_offline_stub() -> bool:
    try:
        out = _gen("__healthcheck__")
    except Exception:
        return True
    return OFFLINE_TAG in out.lower()

FILE_HEADER_RE = re.compile(r"^```file:\s*(?P<path>[^\n]+)\n```(?P<lang>[a-z0-9\-\+_]*)\n", re.IGNORECASE)
FENCE_RE = re.compile(r"```(?P<lang>[a-z0-9\-\+_]*)\n(?P<body>.*?)```", re.DOTALL|re.IGNORECASE)


def _extract_files(markdown: str, root: pathlib.Path) -> List[str]:
    """Supports two forms:
       1) Explicit file header:
          ```file: app/main.py
          ```python
          <code>
          ```
       2) Implicit file blocks annotated in-text like:
          // file: app/main.py   (first line)
          ```python
          <code>
          ```
       If no path is found, files are ignored for runtime.
    """
    written = []
    idx = 0
    while True:
        m = FILE_HEADER_RE.search(markdown, pos=idx)
        if not m:
            break
        path = m.group("path").strip()
        start = m.end()
        fm = FENCE_RE.search(markdown, pos=start)
        if not fm:
            break
        code = fm.group("body")
        outp = root / path
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(code, encoding="utf-8")
        written.append(str(outp))
        idx = fm.end()

    # Fallback: look for "file:" line preceding a code fence
    idx = 0
    while True:
        fm = FENCE_RE.search(markdown, pos=idx)
        if not fm:
            break
        pre = markdown[:fm.start()]
        tail = "\n".join(pre.splitlines()[-2:])
        m2 = re.search(r"file:\s*(?P<path>[^\n]+)", tail, re.IGNORECASE)
        if m2:
            path = m2.group("path").strip()
            code = fm.group("body")
            outp = root / path
            outp.parent.mkdir(parents=True, exist_ok=True)
            outp.write_text(code, encoding="utf-8")
            written.append(str(outp))
        idx = fm.end()
    return written


def _run_cmds(cmds: List[str], cwd: pathlib.Path, timeout_s: int = 180) -> Dict[str, Any]:
    logs = []
    last_rc = 0
    for c in cmds:
        t0 = time.time()
        p = subprocess.run(c, cwd=str(cwd), shell=True, capture_output=True, text=True, timeout=timeout_s)
        dt = time.time() - t0
        logs.append({"cmd": c, "rc": p.returncode, "dt": dt, "stdout": p.stdout, "stderr": p.stderr})
        last_rc = p.returncode
        if p.returncode != 0:
            break
    return {"rc": last_rc, "steps": logs}


def _matches_any(text: str, patterns: List[str]) -> bool:
    for pat in patterns:
        if re.search(pat, text, flags=re.IGNORECASE|re.MULTILINE):
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", required=True, help="YAML with runtime cases")
    ap.add_argument("--out", default="artifacts/build_eval_report.json")
    ap.add_argument("--require_runtime_env", action="store_true",
                    help="If set, skip unless ENABLE_RUNTIME_EVAL=1")
    args = ap.parse_args()

    os.makedirs("artifacts", exist_ok=True)
    suite = yaml.safe_load(open(args.suite, "r", encoding="utf-8"))

    # Auto-skip if offline or runtime disabled
    if _is_offline_stub() or (args.require_runtime_env and os.environ.get("ENABLE_RUNTIME_EVAL") != "1"):
        report = {"suite": args.suite, "skipped": True, "reason": "offline or runtime disabled"}
        pathlib.Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"SKIP runtime suite {args.suite} (offline/runtime-disabled)")
        sys.exit(0)

    agent = Agent()
    total = 0
    passed = 0
    fails: List[str] = []
    case_reports = []

    for case in suite["cases"]:
        total += 1
        prompt = case["prompt"]
        expect_stdout = case.get("expect_stdout_regex", [])
        expect_files = case.get("expect_files", [])
        commands = case.get("commands", [])
        wrk = pathlib.Path(tempfile.mkdtemp(prefix="sildev_"))
        try:
            out = agent.loop(prompt).strip()
            _extract_files(out, wrk)
            missing = [f for f in expect_files if not (wrk / f).exists()]
            if missing:
                case_reports.append({"id": case["id"], "ok": False, "reason": f"missing files {missing}"})
                fails.append(case["id"])
                shutil.rmtree(wrk, ignore_errors=True)
                continue
            run = _run_cmds(commands, wrk)
            ok = (run["rc"] == 0)
            std_all = "\n".join([s["stdout"] for s in run["steps"]])
            if expect_stdout:
                ok = ok and all(re.search(p, std_all, flags=re.IGNORECASE|re.MULTILINE) for p in expect_stdout)
            case_reports.append({"id": case["id"], "ok": ok, "rc": run["rc"], "steps": run["steps"], "workdir": str(wrk)})
            if ok:
                passed += 1
            else:
                fails.append(case["id"])
        except Exception as e:
            case_reports.append({"id": case["id"], "ok": False, "error": repr(e), "workdir": str(wrk)})
            fails.append(case["id"])
        if case_reports[-1]["ok"]:
            shutil.rmtree(wrk, ignore_errors=True)

    summary = {"suite": args.suite, "passed": passed, "total": total, "failed_ids": fails, "cases": case_reports}
    pathlib.Path(args.out).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Runtime suite: Passed {passed}/{total}")
    if fails:
        print("Failed:", ", ".join(fails))
        sys.exit(1)


if __name__ == "__main__":
    main()
