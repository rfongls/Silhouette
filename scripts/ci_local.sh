#!/usr/bin/env bash
set -euo pipefail

section () { echo -e "\n===== $1 ====="; }

section "Environment"
python --version || true
node --version || true
npm --version || true
RC=0

section "Python: Ruff (core + tests)"
if ! command -v ruff >/dev/null 2>&1; then
  echo "Ruff not found (pip install ruff)"
else
  ruff check silhouette_core tests || RC=$?
fi

section "Python: PyTest (full suite; HL7 guarded)"
if ! command -v pytest >/dev/null 2>&1; then
  echo "pytest not found (pip install pytest)"
else
  pytest -q || RC=$?
fi

section "Result"
exit $RC
