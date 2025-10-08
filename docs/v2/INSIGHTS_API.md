# Insights API

Phase 0 ships a lightweight SQLite-backed store that records run history for the Engine UI.

## Schema

* `engine_runs` – pipeline executions (id, pipeline_name, created_at)
* `engine_messages` – messages processed during a run (payload stored as base64 text, JSON metadata)
* `engine_issues` – issues emitted by operators (severity, code, contextual pointers)

Migrations live in `insights/migrations`. Run `alembic upgrade head` to apply the schema.

## Store Helpers

`insights.store.InsightsStore` provides:

* `start_run(pipeline_name)` – insert a run record and return it.
* `record_result(run_id=..., result=...)` – persist a message + issues.
* `summaries()` – aggregated counts for UI consumption.
* `seed()` – populate demo data (used by `python -m insights.store seed`).

## API Endpoints

* `GET /api/insights/summary`
  * Returns totals, per-run breakdown, and top rules.
  * Example response:

```json
{
  "totals": {"runs": 1, "messages": 2, "issues": 3},
  "by_run": [
    {
      "run_id": 1,
      "pipeline": "demo-pipeline",
      "messages": 2,
      "issues": {"error": 1, "warning": 1, "passed": 1},
      "started_at": "2024-07-15T18:00:00Z"
    }
  ],
  "by_rule": [
    {"code": "segment", "severity": "error", "count": 1},
    {"code": "temperature", "severity": "warning", "count": 1}
  ]
}
```

The UI calls this endpoint on load to display the summary table. Seed the store so the response is non-empty during development.
