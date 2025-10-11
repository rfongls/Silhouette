# Engine V2 — Phase Status Log

This document is updated **with each PR** that changes the Engine V2 code or UI. It tracks what was implemented and when.

> Timestamps are ISO-8601 (UTC). If you prefer local time in commits, adjust before merging.

---

## Phase 0 — Skeleton

**Status:** ✅ Completed
**Implemented:** 2025-10-08T00:00:00Z
**Scope:**
- Contracts for adapters, operators, router, and sinks
- Pipeline spec validation (`/api/engine/pipelines/validate`)
- Insights DB + summary endpoint (`/api/insights/summary`)
- Feature-flagged UI entry “Engine (Beta)” with Insights table
- Registry diagnostics endpoint (`/api/engine/registry`)

**Notes:**
- Registry is guaranteed via `engine.plugins` side-effect import.
- Minimal built-ins: `sequence` adapter, `echo` operator, `memory` sink.
- Validation rejects unknown adapters/operators/sinks with a 400 response to match docs.

---

## Phase 0.5 — Demo Runs

**Status:** ✅ Completed
**Implemented:** 2025-10-08T00:00:00Z
**Scope:**
- Execute a pipeline on demand (`POST /api/engine/pipelines/run`)
- Optional persistence into insights store
- UI button “Run demo pipeline” to exercise end-to-end loop

**Notes:**
- Keeps run history visible in Insights without background workers.
- `/api/engine/health` reports version `phase0.5` to align with the demo run capability.

---

## Phase 1 — Adapters & Operators

**Status:** ✅ Completed
**Implemented:** 2025-10-09T00:00:00Z
**Scope:**
- `validate-hl7` now bridges the V1 validator, returning structured `Issue`s (`validate.ok`, `validate.segment.missing`, `validate.structural`, etc.) and respecting `strict` severity promotion.
- `deidentify` wraps the V1 HL7 rules with selector/action mappings, honours `mode: copy|inplace`, and annotates metadata (`meta.deidentified`, `meta.actions`, `meta.deidentify_mode`).
- `mllp` adapter implements a TCP client that reads `<VT>…<FS><CR>` frames and emits `Message(id="mllp-{n}")` with connection metadata.
- Example pipelines added under `examples/engine/phase1.*` and `static/examples/engine/phase1.*`.

**Notes:**
- Config field names stay aligned with V1 to ease migration (`profile`, `strict`, selector syntax like `PID-5.1`, `mode`).
- Tests: `tests/test_op_validate_hl7_e2e.py`, `tests/test_op_deidentify_e2e.py`, `tests/test_adapter_mllp_basic.py`.
- `/api/engine/health` now reports version `phase1` to reflect the completed operator/adapter work.

---

## Phase 2 — Engine UI

**Status:** 🚧 In progress
**Implemented:** 2025-10-12T00:00:00Z
**Scope:**
- Added `pipelines` table + SQLAlchemy model with CRUD helpers and uniqueness guard on name.
- API endpoints for list/get/save/delete stored pipelines plus `/pipelines/{id}/run` for dry vs. persisted runs.
- Engine (Beta) UI lists stored pipelines, provides a YAML editor with live validation, and wires run buttons to Insights refresh.
- Phase 2B polish: toast notifications, YAML diff preview, sync name helper, and Insights run chart.

**Notes:**
- Store auto-creates tables in dev/test if Alembic hasn't run; production should still apply migrations.
- Canvas chart is intentionally lightweight; follow-up will revisit responsiveness and accessibility.

---

## Phase 3 — Background runner & replay

**Status:** ✅ Implemented
**Implemented:** 2025-10-10T00:00:00Z
**Scope:**
- Durable `engine_jobs` queue with leasing metadata, retries, dedupe keys, scheduling, and dead-letter tracking plus supporting indexes.
- Store API for enqueue/lease/heartbeat/start/complete/fail/cancel/retry/list/get with cancel-wins semantics, exponential backoff, and back-pressure enforcement.
- `engine.runner` async worker that leases under a semaphore, executes pipelines, persists results, logs structured events, and respects job payload overrides.
- Replay support via a first-class adapter (`type: replay`) that replays persisted messages when the job kind is `replay`.
- `/api/engine/jobs` endpoints and Engine UI updates: enqueue background runs, list/filter jobs, inspect details, cancel queued/leased/running work, retry dead/canceled jobs, and monitor status/error history.

**Notes:**
- Configuration toggles: `ENGINE_RUNNER_ENABLED`, `ENGINE_RUNNER_CONCURRENCY`, `ENGINE_RUNNER_LEASE_TTL_SECS`, `ENGINE_RUNNER_POLL_INTERVAL_SECS`, `ENGINE_QUEUE_MAX_QUEUED_PER_PIPELINE`.
- Tests cover lifecycle + retry→dead transitions, lease contention, cancellation, replay correctness, and REST validation/dedupe scenarios.

---

## Phase 4 — ML Assist Hooks

**Status:** ✅ Implemented  
**Implemented:** 2025-10-10T00:00:00Z  
**Scope:**
- Assist heuristics to propose allowlist entries and severity downgrades (derived from Insights frequency data).
- Robust z-score anomaly listing comparing recent vs. baseline per-day rates.
- API endpoints (`/api/engine/assist/*`) and Engine UI Assist card for previewing suggestions, inserting commented YAML drafts, and browsing anomalies.
- Test coverage in `tests/test_ml_assist_phase4.py` for suggestion logic and REST flows.

**Notes:** No schema migrations required; Assist computes from existing Insights tables.

---

## Network I/O — MLLP Endpoints

**Status:** ✅ Implemented  
**Implemented:** 2025-10-16T00:00:00Z  
**Scope:**
- `engine_endpoints` table and CRUD helpers for inbound (`mllp_in`) and outbound (`mllp_out`) configurations.
- Inline adapter + `kind:"ingest"` job path so inbound payloads run against existing pipeline specs without edits.
- Async MLLP server with CIDR allowlist enforcement, back-pressure handling, and endpoint lifecycle manager.
- MLLP target sink plus `/api/engine/mllp/send` for ad-hoc transmissions; `/api/engine/endpoints` for create/list/start/stop/delete.
- Engine UI "Endpoints" card to create listeners/targets, inspect status, and send test messages.
- Tests in `tests/test_network_io_mllp.py` covering inbound enqueue, runner execution, outbound delivery, and REST endpoints.

**Notes:** Wildcard binds remain disabled unless `ENGINE_BIND_ANY=1` is set; inbound endpoints require allowlists to accept traffic.
