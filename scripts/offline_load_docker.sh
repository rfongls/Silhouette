#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ ! -d offline/docker ]; then
  echo "offline/docker not found"; exit 2
fi

for tar in offline/docker/*.tar; do
  [ -e "$tar" ] || continue
  echo "[load] $tar"
  docker load -i "$tar"
done
echo "[OK] Docker images loaded"
