# Engine V2 Developer Guide

Phase 0 introduces a minimal runtime, insights persistence, and a feature-flagged UI entry point. Use the documents in this folder for implementation details and the roadmap.

## Quickstart

Validated commands:

```bash
# Apply the initial schema
(cd insights/migrations && alembic upgrade head)

# Populate demo data so the UI is not empty
python -m insights.store seed

# Launch the app with the Engine feature enabled
make engine-dev

# Verify registered components
curl http://localhost:8000/api/engine/registry | jq '.'

# Trigger the demo pipeline (optionally from another terminal)
curl -X POST \
  -H 'Content-Type: application/json' \
  -d "$(python - <<'PY'
import json, pathlib
yaml = pathlib.Path('examples/engine/minimal.pipeline.yaml').read_text()
print(json.dumps({"yaml": yaml, "max_messages": 2, "persist": True}))
PY
)" \
  http://localhost:8000/api/engine/pipelines/run
```

## Reference

* [PHASES.md](PHASES.md) – project roadmap
* [ENGINE_OVERVIEW.md](ENGINE_OVERVIEW.md) – runtime architecture
* [OPERATORS.md](OPERATORS.md) – adapter/operator/sink contracts
* [INSIGHTS_API.md](INSIGHTS_API.md) – storage model and summary API
