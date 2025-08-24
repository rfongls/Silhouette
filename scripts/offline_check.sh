#!/usr/bin/env bash
set -euo pipefail

# Run a minimal Silhouette workflow entirely offline and collect artifacts.

export SILHOUETTE_OFFLINE=1

CMD="silhouette"
if ! command -v silhouette >/dev/null 2>&1; then
  CMD="python -m silhouette_core.cli"
fi

# 1. Repo map (captures run directory)
out=$($CMD repo map . --json-out repo_map.json 2>&1)
echo "$out"
ARTIFACTS=$(echo "$out" | grep -o 'artifacts/[0-9_]*' | head -n1)
if [[ -z "$ARTIFACTS" ]]; then
  echo "Failed to determine artifact directory" >&2
  exit 1
fi

# 2. Hot path analysis
$CMD analyze hotpaths --json >"$ARTIFACTS/hotpaths.json"

# 3. Test suggestions (optional)
$CMD suggest tests src >"$ARTIFACTS/suggest_tests.txt" 2>&1 || true

# 4. CI summary (optional)
$CMD summarize ci --json >"$ARTIFACTS/ci_summary.json" 2>&1 || true

# Final message
cat <<MSG
Artifacts written to $ARTIFACTS:
- $ARTIFACTS/repo_map.json
- $ARTIFACTS/hotpaths.json
- $ARTIFACTS/suggest_tests.txt
- $ARTIFACTS/ci_summary.json
MSG
