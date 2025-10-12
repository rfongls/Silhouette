#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# Silhouette UI — One-click launcher (macOS)
# Creates .venv if missing, installs UI deps, starts Uvicorn, opens browser.
# Double-click this file in Finder. First time only: chmod +x scripts/run_ui.command
# ------------------------------------------------------------------------------
set -euo pipefail

# Resolve repo root (this file lives in scripts/)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

PYEXE="python3"
if ! command -v "$PYEXE" >/dev/null 2>&1; then
  osascript -e 'display alert "Python 3 not found" message "Install Python 3.10+ from python.org"' || true
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
python -m pip install "fastapi>=0.110" "uvicorn[standard]>=0.23" "jinja2>=3.1" "anyio>=4.0" "python-multipart>=0.0.9"

echo
echo "[4/4] Starting server at http://localhost:8000/"
export ENGINE_V2="${ENGINE_V2:-1}"
open "http://localhost:8000/ui/landing" || true
open "http://localhost:8000/ui/engine" || true
open "http://localhost:8000/ui/security/dashboard" || true
open "http://localhost:8000/ui/interop/dashboard" || true
exec python -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload
