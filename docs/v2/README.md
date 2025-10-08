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
```

## Reference

* [PHASES.md](PHASES.md) – project roadmap
* [ENGINE_OVERVIEW.md](ENGINE_OVERVIEW.md) – runtime architecture
* [OPERATORS.md](OPERATORS.md) – adapter/operator/sink contracts
* [INSIGHTS_API.md](INSIGHTS_API.md) – storage model and summary API
