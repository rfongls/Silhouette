#!/usr/bin/env bash
set -euo pipefail

if command -v ruff >/dev/null 2>&1; then
  echo "[ruff]"
  ruff check
fi

if command -v mypy >/dev/null 2>&1; then
  echo "[mypy]"
  mypy
fi

if command -v pytest >/dev/null 2>&1; then
  echo "[pytest]"
  pytest
fi

if command -v bandit >/dev/null 2>&1; then
  echo "[bandit]"
  bandit -r .
fi

if [ -f package.json ]; then
  echo "[npm test]"
  npm ci
  npm test
fi

if command -v hadolint >/dev/null 2>&1; then
  find . -name Dockerfile -print0 | while IFS= read -r -d '' f; do
    echo "[hadolint] $f"
    hadolint "$f"
  done
fi
