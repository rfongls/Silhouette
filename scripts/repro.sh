#!/usr/bin/env bash
set -euo pipefail

# Re-run a recorded Silhouette command. By default, replays the latest run.

ARG="${1:-latest}"
if [[ "$ARG" == "latest" ]]; then
  RUN_JSON="$(ls -1dt artifacts/*/silhouette_run.json 2>/dev/null | head -n1 || true)"
else
  RUN_JSON="$ARG"
  [[ -d "$ARG" ]] && RUN_JSON="$ARG/silhouette_run.json"
fi

if [[ -z "${RUN_JSON:-}" || ! -f "$RUN_JSON" ]]; then
  echo "Run JSON not found. Provide file, artifacts/<ts> dir, or 'latest'." >&2
  exit 1
fi

python - "$RUN_JSON" <<'PY'
import json, sys, subprocess, shlex

p = sys.argv[1]
meta = json.load(open(p, 'r', encoding='utf-8'))
cmd = meta.get("command")
args = meta.get("args") or {}
root = meta.get("repo_root") or "."

def run(cmdline: str) -> None:
    print(">>", cmdline)
    subprocess.run(cmdline, cwd=root, shell=True, check=True)

if cmd == "repo_map":
    out = args.get("out", "artifacts/replay_repo_map.json")
    run(f"silhouette repo map . --json-out {shlex.quote(out)}")
else:
    print(f"Unknown command in run json: {cmd}")
PY

