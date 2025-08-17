import json
import os
import pathlib
import subprocess
import sys
import time


def main() -> None:
    os.makedirs("artifacts", exist_ok=True)
    suite = "eval/suites/basics.yaml"
    cmd = [sys.executable, "-m", "eval.eval", "--suite", suite]
    res = subprocess.run(cmd, capture_output=True, text=True)

    passed_line = ""
    for line in res.stdout.splitlines():
        if line.startswith("Passed "):
            passed_line = line
            break

    report = {
        "ts": time.time(),
        "suite": suite,
        "cmd": " ".join(cmd),
        "stdout": res.stdout,
        "stderr": res.stderr,
        "returncode": res.returncode,
        "passed": passed_line,
        "student_model": os.environ.get("STUDENT_MODEL", ""),
    }

    out_path = pathlib.Path("artifacts/eval_report.json")
    out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(passed_line or f"returncode={res.returncode}")
    sys.exit(res.returncode)


if __name__ == "__main__":
    main()
