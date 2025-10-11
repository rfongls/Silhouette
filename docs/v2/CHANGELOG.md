# Engine V2 — Changelog

## 2025-10-22 — Phase 6C — Advanced UX (partial)

**Highlights**
- Activity Timeline entries now expose quick actions (Start/Stop/Delete endpoint, Cancel job) that confirm in-page without navigation.
- `assist_preview` intent executes locally, summarizing suggested allowlist/severity changes and embedding the draft YAML in results.
- Operators can cancel jobs via natural chat commands or quick-action buttons, both routed through the orchestrator.

**Details**
- Interpreter adds `cancel job <id>`; executor wires to `store.cancel_job` and aggregates summaries for SSE clients.
- Landing page script renders inline buttons per endpoint/job and reuses `/api/agent/execute` for consistent activity logging.
- Timeline summaries now include assist note counts, allowlist entries, and cancellation confirmations.

## 2025-10-21 — Phase 6B — Content Skills (Generate & De-identify)

**Highlights**
- `generate_messages` writes HL7 messages to `${AGENT_DATA_ROOT}/out/<folder>` with guardrails.  
- `deidentify_folder` walks `${AGENT_DATA_ROOT}/in/<folder>/**/*.hl7`, runs the selected pipeline inline, and writes outputs to `${AGENT_DATA_ROOT}/out/<folder>`.  
- Activity timeline entries now include per-action summaries (counts + folders).

**Details**
- New `agent/fs_utils.py` module confines file IO to the agent root and synthesizes demo HL7 payloads.  
- Orchestrator executes both skills in-process and persists summaries to the Activity Log for SSE consumers.  
- Regression test covers generation and de-identification flows end-to-end.

## 2025-10-20 — Phase 6 — Agent Landing & Orchestrator (Demo) — planning

**Highlights**
- Introduces a landing page with **Chat (beta)**, **Preview**, **Run**, and a **live Activity Timeline (SSE)** to confirm actions in-page.  
- Adds agent APIs to **interpret** and **execute** commands without an external LLM.  
- Demo skills: **generate** HL7 files to a folder, **de-identify** a folder into an output bucket.

**Details**
- New `agent_actions` table for activity tracking and live streaming.  
- APIs: `/api/agent/interpret`, `/api/agent/execute`, `/api/agent/registry`, `/api/agent/actions`, `/api/agent/actions/stream`.  
- Docs: `README-agent.md` added.

> User-facing notes per PR. Keep this lean and helpful (what changed, why it matters, and any action required).

## 2025-10-10 — Phase 5 — Network I/O (MLLP Ingest & Send) — shipped

**Highlights**
- Inbound MLLP listeners (bind IP/port + CIDR allowlist) enqueue `ingest` jobs that execute stored pipelines via an inline adapter.
- Outbound delivery through named MLLP targets, the `mllp_target` sink, and an ad-hoc send API for validation.

**Details**
- Added `engine_endpoints` table and CRUD helpers for inbound/outbound definitions.
- Endpoint manager coordinates start/stop lifecycle, updating status/error fields surfaced via API/UI.
- Default deny inbound posture with CIDR allowlists and env-gated wildcard binding.

## 2025-10-10 — Phase 4 — ML Assist Hooks

**Highlights**
- Assist service proposes allowlist and severity tuning hints derived from recent Insights frequency data.
- Robust z-score anomaly surfacing flags outlier issue codes/segments across recent vs. baseline windows.
- Engine UI gains an Assist card to preview suggestions, view anomalies, and insert a commented YAML draft (no auto-apply).

**Details**
- Endpoints: `POST /api/engine/assist/preview`, `GET /api/engine/assist/anomalies`.
- Suggestions render as commented YAML blocks so operators review before applying.
- Tests added in `tests/test_ml_assist_phase4.py` to validate suggestion heuristics and REST responses.

## 2025-10-10 — Phase 3 — Background runner, replay, and UI

**Highlights**
- Shipped the durable `engine_jobs` queue with leasing/retry metadata, store helpers, and the async `engine.runner` worker.
- Added a replay adapter (`type: replay`) plus API/runner wiring so prior runs can be reprocessed in the background.
- Engine UI now supports "Run in background" and surfaces a Jobs table with status chips, cancel/retry actions, and error previews.

**Details**
- `/api/engine/jobs` exposes enqueue/list/get/cancel/retry with dedupe (409) and back-pressure (429) safeguards.
- Runner logs structured `job.start/success/error` frames, honors cancel-wins semantics, and applies exponential backoff.
- Replay jobs persist a new run (when requested) and tag messages with `replay` metadata for downstream analysis.

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
