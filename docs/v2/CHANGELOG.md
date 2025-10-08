# Engine V2 — Changelog

> User-facing notes per PR. Keep this lean and helpful (what changed, why it matters, and any action required).

## 2025-10-08 — Phase 0.5 follow-up

**Highlights**
- Engine health endpoint now advertises `phase0.5`.
- Documented the Pydantic v1 compatibility contract for spec models.

**Details**
- `/api/engine/health` exposes the current phase string so operators can confirm demo-run support is present.
- Added a compatibility note in `docs/v2/ENGINE_OVERVIEW.md` clarifying that spec models must remain Pydantic v1-friendly until the stack migrates.

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
  - Validation now returns `400` when adapters/operators/sinks are missing from the registry
- New examples:
  - `static/examples/engine/minimal.pipeline.yaml`
- Docs:
  - `docs/v2/STATUS.md` & PR template require status+changelog updates per PR

**Action required for developers**
- When changing anything under `engine/` or `insights/`, update:
  - `docs/v2/STATUS.md` with a new timestamped entry
  - `docs/v2/CHANGELOG.md` with a brief user-facing note
