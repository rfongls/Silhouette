#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ ! -f offline/requirements.lock ]; then
  echo "offline/requirements.lock not found"; exit 2
fi

mkdir -p offline/wheels
python -m pip install -U pip
# download all wheels into offline/wheels
pip download -d offline/wheels -r offline/requirements.lock

echo "[OK] Wheels saved to offline/wheels"
ls -1 offline/wheels | wc -l | xargs echo "Wheel files:"
exit 0
