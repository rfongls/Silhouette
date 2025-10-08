# Engine V2 Phases

> **Last updated:** 2025-10-06 (UTC)

## Phase 0 – Skeleton (✅ Completed 2025-10-06)

* Contracts for adapters, operators, router, and sinks.
* Pipeline spec validation and registry bootstrap.
* Insights database + API summary endpoint.
* Feature-flagged UI entry (Engine Beta) with stubbed pipeline and insights sections.

## Phase 0.5 – Demo runs (✅ Completed 2025-10-06)

* `POST /api/engine/pipelines/run` executes a YAML spec with optional persistence.
* Engine (Beta) page exposes a **Run demo pipeline** button wired to the run endpoint.

## Phase 1 – Adapters & Operators (🚧 In progress)

* Implement concrete adapters (MLLP, File) and operators (Validate, Deid).
* CRUD endpoints for pipeline specs.
* Persist pipeline definitions in the insights store.

## Phase 2 – Engine UI (🔜 Planned)

* Pipelines list + detail configuration.
* Front-end run / dry-run controls (no background runner).
* Insights charts for error/warning/passed trends.

## Phase 3 – Background Runner & Replay (🔜 Planned)

* Supervisor, back-pressure, retry policy, and dead-letter queue.
* Replay pipelines from stored runs.

## Phase 4 – ML Assist Hooks (🔜 Planned)

* Allowlist suggestor endpoint and anomaly baselines.
* UI hints driven by ML assist results.
* Draft config suggestions without auto-apply.

---

### Process
- Each PR that changes Engine/Insights must update: `docs/v2/STATUS.md` and `docs/v2/CHANGELOG.md`.
- When scope changes, also update this file to mark phase state and date.
- Prefer ISO-8601 UTC timestamps (e.g. `2025-10-08T00:00:00Z`).
