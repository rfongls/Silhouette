# Engine V2 — Changelog

> User-facing notes per PR. Keep this lean and helpful (what changed, why it matters, and any action required).

## 2025-10-12 — Phase 2B UX polish

**Highlights**
- Added toast notifications for pipeline saves, runs, deletes, and validation feedback.
- YAML diff preview (before vs. current editor state) and a one-click "Sync name → YAML" helper.
- Insights chart displaying grouped bars (errors, warnings, passed) for the latest runs.

**Details**
- Diff preview uses a lightweight in-page LCS implementation with no external dependencies.
- Canvas-based chart renderer mirrors Insights summary data and redraws on demand.
- Editor diff resets after validation/save to avoid stale comparisons.

## 2025-10-11 — Phase 2 pipeline CRUD + UI shell

**Highlights**
- Pipelines can now be saved in the Insights store with name/description/YAML/spec metadata and listed/edited/deleted via API.
- Engine (Beta) page lists stored pipelines, opens a YAML editor with live validation, and adds dry vs. persisted run buttons that refresh Insights.

**Details**
- Added `pipelines` table + SQLAlchemy model and CRUD helpers (auto-created for dev/test environments).
- New endpoints: `GET/POST/DELETE /api/engine/pipelines`, `GET /api/engine/pipelines/{id}`, `POST /api/engine/pipelines/{id}/run`.
- UI wiring: status badges in table, editor defaults, and Insights summary refresh after persisted runs.

## 2025-10-10 — SQL framed logging

**Highlights**
- Insights and engine SQL activity now writes framed entries to `out/interop/server_sql.log` with parameter redaction and timing when debug logging is enabled.

**Details**
- Added reusable `install_sql_logging(engine)` helper that mirrors the HTTP middleware toggle semantics and survives logger failures via fallback writes.
- Instrumented `insights.store` so the shared engine automatically emits SQL frames; tests cover redaction and framing.

## 2025-10-09 — Phase 1 adapters/operators

**Highlights**
- Engine V2 pipelines can validate and de-identify HL7 messages using the legacy rule engines.
- Added an MLLP client adapter for live TCP feeds plus file/memory demo pipelines.
- Hardened de-identification: per-rule exceptions no longer break the run; they emit `deidentify.rule.error`.
- HTTP logs: JSON bodies are parsed and redacted (same key set as headers/query).

**Details**
- `validate-hl7` emits structured `Issue`s (`validate.ok`, `validate.segment.missing`, `validate.structural`) and respects the `strict` flag.
- `deidentify` applies selector-based actions (`PID-5.1`, `PID-13`, etc.), supports `mode: copy|inplace`, and annotates metadata for downstream sinks.
- Implemented MLLP framing (`<VT>…<FS><CR>`), added example YAMLs under `examples/engine/phase1.*` and `static/examples/engine/phase1.*`, and covered the new features with targeted tests.

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
