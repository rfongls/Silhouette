#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# Silhouette UI — One-click launcher (Linux)
# Creates .venv if missing, installs UI deps, starts Uvicorn, opens browser.
# Make executable: chmod +x scripts/run_ui.sh
# Double-click in your file manager or run: ./scripts/run_ui.sh
# ------------------------------------------------------------------------------
set -euo pipefail

# Resolve repo root (this file lives in scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# Choose python
PYEXE="${PYEXE:-python3}"
if ! command -v "$PYEXE" >/dev/null 2>&1; then
  echo "Python 3 not found. Please install Python 3.10+ and retry." >&2
  exit 1
fi

echo
echo "[1/4] Ensuring virtual env: .venv"
if [ ! -d ".venv" ]; then
  "$PYEXE" -m venv .venv
fi
source .venv/bin/activate

echo
echo "[2/4] Upgrading pip"
python -m pip install -U pip

echo
echo "[3/4] Installing UI dependencies (fastapi, uvicorn, jinja2, anyio, python-multipart)"
python -m pip install \
  "fastapi>=0.110" \
  "uvicorn[standard]>=0.23" \
  "jinja2>=3.1" \
  "anyio>=4.0" \
  "python-multipart>=0.0.9"

PORT="${PORT:-8000}"
HOST="${HOST:-127.0.0.1}"
URL="http://"${HOST}:${PORT}"/ui/security/dashboard"

echo
echo "[4/4] Starting server at http://${HOST}:${PORT}/"

# Try to open the browser (xdg-open is the freedesktop standard)
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL" >/dev/null 2>&1 || true
elif command -v gio >/dev/null 2>&1; then
  gio open "$URL" >/dev/null 2>&1 || true
fi

exec python -m uvicorn main:app --host "$HOST" --port "$PORT"
