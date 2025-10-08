#!/usr/bin/env bash
set -euo pipefail

# Fail fast if Engine/Insights changed but status docs weren't updated.
# This is intentionally simple: runs in CI and locally.

CHANGED=$(git diff --name-only origin/${GITHUB_BASE_REF:-main}...HEAD || true)

# If git range is not available (local), use last commit as a fallback.
if [ -z "${CHANGED}" ]; then
  CHANGED=$(git diff --name-only HEAD~1...HEAD || true)
fi

needs_docs=""
if echo "${CHANGED}" | grep -E '^(engine/|insights/)' >/dev/null 2>&1; then
  needs_docs="yes"
fi

if [ -n "${needs_docs}" ]; then
  if ! echo "${CHANGED}" | grep -E '^docs/v2/STATUS.md$' >/dev/null 2>&1; then
    echo "::error ::Engine/Insights changed but docs/v2/STATUS.md not updated."
    exit 1
  fi
  if ! echo "${CHANGED}" | grep -E '^docs/v2/CHANGELOG.md$' >/dev/null 2>&1; then
    echo "::error ::Engine/Insights changed but docs/v2/CHANGELOG.md not updated."
    exit 1
  fi
fi

echo "Docs check passed."
