#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

IMAGES_FILE="offline/docker/IMAGES.txt"
mkdir -p offline/docker
if [ ! -f "$IMAGES_FILE" ]; then
  echo "$IMAGES_FILE not found"; exit 2
fi

while IFS= read -r image; do
  [ -z "$image" ] && continue
  case "$image" in \#*) continue ;; esac
  echo "[pull] $image"
  docker pull "$image"
  fname="$(echo "$image" | tr '/:' '__').tar"
  echo "[save] $image -> offline/docker/$fname"
  docker save -o "offline/docker/$fname" "$image"
done < "$IMAGES_FILE"

echo "[OK] Docker images saved to offline/docker"
