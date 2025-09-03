#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ ! -d offline/wheels ]; then
  echo "offline/wheels not found"; exit 2
fi
if [ ! -f offline/requirements.lock ]; then
  echo "offline/requirements.lock not found"; exit 2
fi

python -m pip install -U pip
pip install --no-index --find-links offline/wheels -r offline/requirements.lock

echo "[OK] Installed from offline wheelhouse"
