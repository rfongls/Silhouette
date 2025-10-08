# Engine V2 — Changelog

> User-facing notes per PR. Keep this lean and helpful (what changed, why it matters, and any action required).

## 2025-10-08 — Phase 0.5 follow-up

**Highlights**
- `/api/engine/health` now reports version `phase0.5` for demo-run capable builds.
- Consolidated Engine V2 documentation into `PHASES.md` with inline spec/schema and updated Pydantic v1 compatibility guidance.

**Details**
- Health endpoint exposes the current phase string so operators can confirm demo-run support is present.
- Engine documentation now lives in a single source (`docs/v2/PHASES.md`), and spec models are explicitly documented as Pydantic v1-compatible until the stack upgrades.

## 2025-10-06 — Phase 0 & Phase 0.5

**Highlights**
- Phase 0 Skeleton + Insights + UI entry + Registry endpoint
- Phase 0.5 demo run endpoint; UI “Run demo pipeline” button

**Details**
- New endpoints:
  - `GET /api/engine/registry` — list registered adapters/operators/sinks
  - `POST /api/engine/pipelines/validate` — normalize/validate YAML specs (now rejects unknown components)
  - `POST /api/engine/pipelines/run` — run a spec, optionally persist results
  - `GET /api/insights/summary` — aggregate counts consumed by UI
- New examples:
  - `static/examples/engine/minimal.pipeline.yaml`
- Docs & process:
  - Status log (`docs/v2/STATUS.md`) and changelog require updates with each Engine/Insights change
  - PR template + docs check enforce keeping the single-source docs in sync

**Action required for developers**
- When changing anything under `engine/` or `insights/`, update:
  - `docs/v2/STATUS.md` with a new timestamped entry
  - `docs/v2/PHASES.md` with spec/process changes
  - `docs/v2/CHANGELOG.md` with a brief user-facing note
