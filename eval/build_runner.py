import argparse
import json
import os
import re
import shutil
import subprocess
import shlex
import sys
import tempfile
import time
import pathlib
import yaml
from typing import Dict, Any, List
from silhouette_core.agent_loop import Agent
from silhouette_core.response_engine import generate_text as _gen
from security.redaction import DEFAULT_REDACTOR as _redactor

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


def _zip_and_cleanup(wrk: pathlib.Path, suite_name: str, case_id: str, keep: bool = False) -> str:
    """Archive workdir to artifacts/runs/<suite>/<case_id>.zip and optionally remove it."""
    zipdir = pathlib.Path("artifacts") / "runs" / suite_name
    zipdir.mkdir(parents=True, exist_ok=True)
    zip_base = zipdir / case_id
    shutil.make_archive(str(zip_base), "zip", wrk)
    if not keep:
        shutil.rmtree(wrk, ignore_errors=True)
    return str(zip_base.with_suffix(".zip"))


def _run_cmds(
    cmds: List[str],
    cwd: pathlib.Path,
    timeout_s: int = 600,
    docker_image: str | None = None,
    docker_extra: str | None = None,
) -> Dict[str, Any]:
    logs = []
    last_rc = 0
    for c in cmds:
        t0 = time.time()
        if docker_image:
            extra = docker_extra or ""
            cmd = (
                f"docker run --rm -v {cwd}:/workspace -w /workspace "
                f"{extra} {docker_image} bash -lc {shlex.quote(c)}"
            )
        else:
            cmd = c
        p = subprocess.run(
            cmd,
            cwd=str(cwd),
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        dt = time.time() - t0
        logs.append(
            {
                "cmd": _redactor.redact_text(c),
                "rc": p.returncode,
                "dt": dt,
                "stdout": _redactor.redact_text(p.stdout),
                "stderr": _redactor.redact_text(p.stderr),
            }
        )
        last_rc = p.returncode
        if p.returncode != 0:
            break
    return {"rc": last_rc, "steps": logs}


def _redact_workdir(wrk: pathlib.Path) -> None:
    """Redact text files within a workdir."""
    exts = {".txt", ".md", ".json", ".yaml", ".yml", ".py", ".log"}
    for p in wrk.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts and p.stat().st_size <= 200_000:
            try:
                txt = p.read_text(encoding="utf-8")
            except Exception:
                continue
            p.write_text(_redactor.redact_text(txt), encoding="utf-8")


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
        docker_image = case.get("image") if case.get("runtime") == "docker" else None
        docker_extra = case.get("docker_extra", "")
        wrk = pathlib.Path(tempfile.mkdtemp(prefix="sildev_"))
        case_prompt = prompt
        try:
            out = agent.loop(prompt).strip()
            _extract_files(out, wrk)
            missing = [f for f in expect_files if not (wrk / f).exists()]
            if missing:
                _redact_workdir(wrk)
                zip_path = _zip_and_cleanup(wrk, suite.get("name", "suite"), case["id"])
                case_reports.append({
                    "id": case["id"],
                    "ok": False,
                    "reason": f"missing files {missing}",
                    "prompt": _redactor.redact_text(case_prompt),
                    "workdir": zip_path,
                })
                fails.append(case["id"])
                continue
            run = _run_cmds(commands, wrk, docker_image=docker_image, docker_extra=docker_extra)
            ok = (run["rc"] == 0)
            std_all = "\n".join([s["stdout"] for s in run["steps"]])
            if expect_stdout:
                ok = ok and all(re.search(p, std_all, flags=re.IGNORECASE|re.MULTILINE) for p in expect_stdout)
            _redact_workdir(wrk)
            zip_path = _zip_and_cleanup(wrk, suite.get("name", "suite"), case["id"], keep=not ok)
            case_reports.append({
                "id": case["id"],
                "ok": ok,
                "rc": run["rc"],
                "steps": run["steps"],
                "workdir": zip_path,
                "prompt": _redactor.redact_text(case_prompt),
            })
            if ok:
                passed += 1
            else:
                fails.append(case["id"])
        except Exception as e:
            zip_path = _zip_and_cleanup(wrk, suite.get("name", "suite"), case["id"], keep=True)
            case_reports.append({
                "id": case["id"],
                "ok": False,
                "error": repr(e),
                "workdir": zip_path,
                "prompt": _redactor.redact_text(case_prompt),
            })
            fails.append(case["id"])

    summary = {"suite": args.suite, "passed": passed, "total": total, "failed_ids": fails, "cases": case_reports}
    pathlib.Path(args.out).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Runtime suite: Passed {passed}/{total}")
    if fails:
        print("Failed:", ", ".join(fails))
        sys.exit(1)


if __name__ == "__main__":
    main()
