#!/usr/bin/env bash
set -euo pipefail

export ENGINE_V2=${ENGINE_V2:-1}
export INSIGHTS_DB_URL=${INSIGHTS_DB_URL:-"sqlite:///$(pwd)/data/insights.db"}

exec uvicorn server:app --reload --host 0.0.0.0 --port 8000
