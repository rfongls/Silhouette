# Engine V2 Phases

## Phase 0 – Skeleton (current)

* Contracts for adapters, operators, router, and sinks.
* Pipeline spec validation and registry bootstrap.
* Insights database + API summary endpoint.
* Feature-flagged UI entry (Engine Beta) with stubbed pipeline and insights sections.

## Phase 1 – Adapters & Operators

* Implement concrete adapters (MLLP, File) and operators (Validate, Deid).
* CRUD endpoints for pipeline specs.
* Persist pipeline definitions in the insights store.

## Phase 2 – Engine UI

* Pipelines list + detail configuration.
* Front-end run / dry-run controls (no background runner).
* Insights charts for error/warning/passed trends.

## Phase 3 – Background Runner & Replay

* Supervisor, back-pressure, retry policy, and dead-letter queue.
* Replay pipelines from stored runs.

## Phase 4 – ML Assist Hooks

* Allowlist suggestor endpoint and anomaly baselines.
* UI hints driven by ML assist results.
* Draft config suggestions without auto-apply.
