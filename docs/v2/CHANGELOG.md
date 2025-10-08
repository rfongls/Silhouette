# Engine V2 — Changelog

> User-facing notes per PR. Keep this lean and helpful (what changed, why it matters, and any action required).

## 2025-10-08 — Phase 0 & Phase 0.5

**Highlights**
- Phase 0 Skeleton + Insights + UI entry + Registry endpoint
- Phase 0.5 demo run endpoint; UI “Run demo pipeline” button

**Details**
- New endpoints:
  - `GET /api/engine/registry` — list registered adapters/operators/sinks
  - `POST /api/engine/pipelines/validate` — normalize/validate YAML specs
  - `POST /api/engine/pipelines/run` — run a spec, optionally persist results
  - `GET /api/insights/summary` — aggregate counts consumed by UI
- New examples:
  - `static/examples/engine/minimal.pipeline.yaml`
- Docs:
  - `docs/v2/STATUS.md` & PR template require status+changelog updates per PR

**Action required for developers**
- When changing anything under `engine/` or `insights/`, update:
  - `docs/v2/STATUS.md` with a new timestamped entry
  - `docs/v2/CHANGELOG.md` with a brief user-facing note
