# Engine V2 — Phases & Spec (Single Source of Truth)

**Last updated:** 2025-10-12 (UTC)

This file is the **only** spec/runbook for Engine V2. It includes:
- Quickstart & verification commands
- Runtime & data contracts
- Pipeline spec (normative) + JSON Schema (inline)
- API endpoints (engine + insights)
- Insights storage model
- Phase checklists & acceptance criteria (including Phase 1)
- PR checklist expectations

> Keep **STATUS.md** and **CHANGELOG.md** updated with each PR. All technical details live here.

---

## Quickstart (verified)

```bash
# 1) Apply schema (SQLite by default)
(cd insights/migrations && alembic upgrade head)

# 2) Seed demo insights so UI isn't empty
python -m insights.store seed

# 3) Launch with Engine V2 enabled
make engine-dev

# 4) Verify registry
curl http://localhost:8000/api/engine/registry | jq '.'

# 5) Run the demo pipeline (two messages, persisted)
curl -X POST \
  -H 'Content-Type: application/json' \
  -d "$(python - <<'PY'
import json, pathlib
yaml = pathlib.Path('examples/engine/minimal.pipeline.yaml').read_text()
print(json.dumps({"yaml": yaml, "max_messages": 2, "persist": True}))
PY
)" \
  http://localhost:8000/api/engine/pipelines/run
```

---

## Runtime & Contracts (summary)

- **Contracts:** `engine/contracts.py`
  - `Message(id: str, raw: bytes, meta: dict[str, Any])`
  - `Issue(severity: Literal["error","warning","passed"], code: str, …pointers…, message?: str)`
  - `Result(message: Message, issues: list[Issue])`
- **ABCs:**
  - `Adapter.stream() -> AsyncIterator[Message]`
  - `Operator.process(Message) -> Result`
  - `Sink.write(Result) -> None`
- **Registry:** `engine/registry.py` provides `register_*` helpers and factories.
- **Runtime:** `engine/runtime.py`
  - Builds pipeline from spec (adapter → operators → sinks) and broadcasts results.
  - `EngineRuntime(spec).run(max_messages=…)` returns a list of `Result`.
- **Plugins:** `engine/plugins.py` ensures built-ins & stubs are registered:
  - Adapters: `sequence`, `file`, `mllp` (stub in Phase 0.5)
  - Operators: `echo`, `validate-hl7` (stub in Phase 0.5), `deidentify` (stub in Phase 0.5)
  - Sinks: `memory`
- **Pydantic:** v1 is the baseline for spec parsing to match FastAPI 0.95.x. Avoid v2-only APIs until the stack upgrades.
- **Router:** `router.strategy` is normalized but ignored in phases 0/0.5 (broadcast behaviour).

---

## Pipeline Spec (normative)

### Shape (YAML)

```yaml
version: "1"                   # normalized to string
name: "<pipeline-name>"        # required
adapter:
  type: "<registered-adapter>" # sequence | file | mllp
  config: {}                   # adapter-specific
operators:                     # 0..N
  - type: "<registered-operator>"  # echo | validate-hl7 | deidentify
    config: {}
router:
  strategy: "broadcast"        # placeholder until Phase 2
  config: {}
sinks:                         # 1..N
  - type: "<registered-sink>"  # memory
    config: {}
metadata: {}                   # free-form
```

**Normalization rules**
- `version` → string
- `type` and `router.strategy` → lowercased, trimmed
- `operators` / `sinks` accept a single object or list → normalized to list
- Unknown component names cause `/api/engine/pipelines/validate` to return **400** with the missing items (e.g., `adapter:unknown`).

**Minimal example**: `examples/engine/minimal.pipeline.yaml`

```yaml
version: 1
name: demo-sequence
adapter:
  type: sequence
  config:
    messages:
      - id: demo-1
        text: "Vitals inbound"
        preview: "ADT^A01"
      - id: demo-2
        text: "ADT update"
operators:
  - type: echo
    config:
      note: "Phase 0 demo operator"
sinks:
  - type: memory
    config:
      label: "dev-memory"
metadata:
  owner: "interoperability"
```

### JSON Schema (optional external validation)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://silhouette.example.com/schemas/engine/v2/pipeline.schema.json",
  "title": "Silhouette Engine V2 Pipeline",
  "type": "object",
  "additionalProperties": false,
  "required": ["version", "name", "adapter", "sinks"],
  "properties": {
    "version": { "type": ["string", "number"] },
    "name": { "type": "string", "minLength": 1 },
    "adapter": { "$ref": "#/$defs/component" },
    "operators": {
      "oneOf": [
        { "$ref": "#/$defs/component" },
        { "type": "array", "items": { "$ref": "#/$defs/component" } }
      ],
      "default": []
    },
    "router": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "strategy": { "type": "string", "default": "broadcast" },
        "config": { "type": "object" }
      },
      "default": { "strategy": "broadcast", "config": {} }
    },
    "sinks": {
      "oneOf": [
        { "$ref": "#/$defs/component" },
        { "type": "array", "items": { "$ref": "#/$defs/component" }, "minItems": 1 }
      ]
    },
    "metadata": { "type": "object", "default": {} }
  },
  "$defs": {
    "component": {
      "type": "object",
      "required": ["type"],
      "additionalProperties": false,
      "properties": {
        "type": { "type": "string", "minLength": 1 },
        "config": { "type": "object", "default": {} }
      }
    }
  }
}
```

---

## Engine & Insights API

**Engine**
- `GET /api/engine/health` → `{ ok: true, version: "phase2", feature: "engine-v2" }`
- `GET /api/engine/registry` → registered adapters/operators/sinks
- `GET /api/engine/pipelines` → list stored pipelines (`{ items: [...] }`)
- `GET /api/engine/pipelines/{id}` → retrieve full YAML/spec for editing
- `POST /api/engine/pipelines/validate` → `{ spec }` or **400** (invalid YAML / unknown components)
- `POST /api/engine/pipelines` → create/update stored pipelines (normalizes spec)
- `DELETE /api/engine/pipelines/{id}` → remove stored pipeline
- `POST /api/engine/pipelines/run` → `{ run_id?, processed, issues: {error, warning, passed}, spec }`
- `POST /api/engine/pipelines/{id}/run` → run a stored pipeline with `persist` toggle

**Insights**
- `GET /api/insights/summary` → totals, by_run, by_rule

**Insights summary example**
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

---

## Insights storage model (SQLite default)

Tables:
- `engine_runs (id, pipeline_name, created_at)`
- `engine_messages (id, run_id → engine_runs.id, message_id, payload (base64 text), meta (JSON), created_at)`
- `engine_issues (id, message_id → engine_messages.id, severity, code, segment, field, component, subcomponent, value, message)`
- `pipelines (id, name UNIQUE, description, yaml TEXT, spec JSON, created_at, updated_at)`

Migrations live under `insights/migrations`.
Set `INSIGHTS_DB_URL` to override the DSN.
Seed data via `python -m insights.store seed`.

---

## Phase 0 — Skeleton (✅ Completed 2025-10-08)

**Scope**
- Contracts, registry bootstrap, spec parsing & normalization (Pydantic v1)
- Insights DB + API summary endpoint
- Feature-flagged UI entry (Engine Beta)
- Registry diagnostics endpoint

**Acceptance (met)**
- Health & Registry endpoints return expected fields
- Validate endpoint normalizes and rejects unknown components with **400**
- Seeding + UI Insights work end-to-end

---

## Phase 0.5 — Demo runs (✅ Completed 2025-10-08)

**Scope**
- `POST /api/engine/pipelines/run` executes a YAML spec with `max_messages` / `persist`
- Engine (Beta) UI exposes a **Run demo pipeline** button that refreshes Insights after completion

**Acceptance (met)**
- Running the demo spec persists a run and the summary reflects new messages/issues

---

## Phase 1 — Adapters & Operators (✅ Completed)

**What shipped**
- `validate-hl7` operator now wraps the V1 validator, emits structured `Issue`s (`validate.ok`, `validate.segment.missing`, `validate.structural`, etc.), and respects the `strict` flag when promoting warnings to errors.
- `deidentify` operator invokes the V1 HL7 rule engine with selector→action mappings, preserves `mode: copy|inplace` semantics, and annotates metadata (`meta.deidentified`, `meta.actions`, `meta.deidentify_mode`).
- `mllp` adapter implements a TCP client that frames `<VT>…<FS><CR>` payloads and yields `Message(id="mllp-{n}")` with connection metadata.
- Phase 1 example pipelines added under `examples/engine/` and `static/examples/engine/` (file + mllp sources).
- End-to-end tests cover validation, de-identification, and the MLLP adapter loopback.

**Operator: `validate-hl7` (V2 → V1 mapping)**
```yaml
type: validate-hl7
config:
  profile: "<string|null>"   # e.g., "ADT_A01" or "default"
  strict: <bool>             # match V1 semantics
  # retain other V1-compatible flags as-is
```
Behaviour:
- Input: HL7 text in `Message.raw` (decoded with UTF-8 + replacement semantics).
- Delegate to the V1 validator and convert findings → `Issue` (severity, rule code, pointers when available).
- Missing required segments (e.g., `PV1`) surface as `validate.segment.missing` (warning when `strict=false`, error when `strict=true`).
- Structural validation errors escalate to `error` when `strict=true`, `warning` otherwise; missing `hl7apy` results in a `validate.structural.unavailable` warning.
- Output: `Result.message` preserves the original message object.

**Operator: `deidentify` (V2 → V1 mapping)**
```yaml
type: deidentify
config:
  actions:
    "PID-5.1": "remove"
    "PID-13":  "mask"
  mode: "copy"  # or "inplace" (default: copy)
```
Behaviour:
- Invoke the existing V1 de-identification pipeline via `apply_single_rule` per selector.
- `mode: copy` returns a new `Message` instance (original untouched); `mode: inplace` mutates the original payload/meta in place.
- Always set `meta.deidentified = true`, copy `actions` into metadata, and set `meta.deidentify_mode`.
- Emit at least one `passed` issue (`deidentify.applied`) plus rule-level warnings for invalid selectors, unsupported actions, or unmatched fields.
- If a rule raises, record `deidentify.rule.error` and continue processing.
- HTTP middleware now redacts secret keys inside JSON request body previews (parity with header/query redaction).
- SQL logging attaches automatically to the Insights engine and writes framed entries to `out/interop/server_sql.log` (debug toggle + HTTP force tokens mirrored from middleware).

**Adapter: `mllp`**
```yaml
type: mllp
config:
  host: "127.0.0.1"
  port: 2575
  connect_timeout: 3.0
  role: "client"   # server optional in later phases
```
Behaviour (client):
- Connect to remote MLLP endpoint, read <VT>...<FS><CR> frames
- Yield `Message(id="mllp-{n}")` with `meta={"adapter": "mllp", "host": …, "port": …}` per frame
- Raise on connection timeout or truncated frames; close sockets on cancellation

**Example pipeline (Phase 1 demo)**
```yaml
version: 1
name: phase1-validate-deid-demo
adapter:
  type: file
  config:
    paths: ["data/hl7/demo.hl7"]
operators:
  - type: validate-hl7
    config:
      profile: "ADT_A01"
      strict: false
  - type: deidentify
    config:
      actions: {"PID-5.1": "remove", "PID-13": "mask"}
      mode: "copy"
sinks:
  - type: memory
    config: { label: "dev-memory" }
```

**Acceptance tests (implemented)**
- `tests/test_op_validate_hl7_e2e.py` – validates happy-path (`validate.ok`) and missing `PV1` severity flip with `strict`.
- `tests/test_op_deidentify_e2e.py` – asserts PID redaction/masking, metadata annotations, and copy vs. inplace behaviour.
- `tests/test_adapter_mllp_basic.py` – loopback server sends two frames; adapter yields `mllp-1`, `mllp-2` with raw payloads intact.

**Done criteria**
- ✅ Implementations + tests passing (`pytest -q`).
- ✅ Documentation updated (this file + `STATUS.md` + `CHANGELOG.md`).

---

## Phase 2 — Engine UI (🚧 In progress)

**Scope (Phase 2A)**
- Persisted pipelines table (name/description/YAML/spec) behind CRUD API + SQLAlchemy model
- UI card with pipeline table (list, edit, delete) and YAML editor with live validation
- Dry-run vs. persisted run buttons that refresh Insights summary on completion

**Acceptance (current sprint)**
- Creating, updating, and deleting pipelines succeeds via API/UI
- Stored pipelines can run in dry or persisted mode from UI, showing status feedback
- Persisted runs write to Insights immediately and the summary refresh reflects new counts

**Phase 2B (this PR)**
- Toast notifications for pipeline actions (save, validate, run, delete)
- YAML diff preview (before vs. current editor state)
- "Sync name → YAML" helper to keep spec names aligned
- Insights chart (grouped bars for recent run issues)

**Next**
- Toast UX accessibility polish (focus, stacking limits)
- Enhanced diff view (side-by-side + copy helpers)
- Insights filters (per pipeline, timeframe selection)

## Phase 3 — Background Runner & Replay (✅ Implemented)

**Goal**

Deliver a durable background execution path so stored pipelines can run asynchronously with retries, back-pressure, replay support, and a lightweight UI for operators to manage work.

**What shipped**

- **Queue & model**: `engine_jobs` table (SQLAlchemy model + Alembic migration) stores pipeline id, job kind (`run`/`replay`), payload overrides, lifecycle status, priority, attempts/max attempts, scheduling metadata, leasing fields, optional dedupe key, run linkage, and last error text. Supporting indexes keep leasing and back-pressure lookups fast.
- **Store helpers**: `enqueue_job`, `lease_jobs`, `heartbeat_job`, `start_job`, `complete_job`, `fail_job_and_maybe_retry`, `cancel_job`, `retry_job`, `list_jobs`, and `get_job` implement optimistic leasing, dedupe race handling, configurable back-pressure, cancel-wins semantics, and retry/backoff logic.
- **Runner service**: `engine.runner.EngineRunner` continuously leases jobs under a semaphore, executes pipelines through `EngineRuntime`, persists results when requested, records structured logs (`job.start/success/error`), and applies exponential backoff with dead-letter promotion. CLI entrypoint (`python -m engine.runner`) and `make engine-runner` target wire it up.
- **Replay adapter**: `type: replay` streams previously persisted messages by `run_id`, rehydrating payload/meta (with replay markers) so pipelines can rerun prior traffic. Runner swaps in the adapter automatically for `kind="replay"` jobs using the job payload's `replay_run_id`.
- **API surface**: `/api/engine/jobs` endpoints allow enqueue, list/filter, fetch details, cancel (`queued|leased|running`), and retry (`dead|canceled`) jobs with dedupe (409), back-pressure (429), and validation (400/404) handling. Responses expose payloads for observability and UI hooks.
- **UI hooks**: Engine dashboard gains a "Run in background" action per pipeline plus a Jobs table (status chips, attempts, scheduled time, last error preview, cancel/retry buttons, manual refresh).
- **Tests**: Coverage spans lifecycle transitions, retry→dead promotion, runner execution, API flows, and replay round-trips (verifying replayed runs recreate prior messages with replay metadata).
- **Docs**: This runbook, STATUS, and CHANGELOG document the shipped behavior.

**Configuration**

- `ENGINE_RUNNER_ENABLED`, `ENGINE_RUNNER_CONCURRENCY`, `ENGINE_RUNNER_LEASE_TTL_SECS`, `ENGINE_RUNNER_POLL_INTERVAL_SECS`, `ENGINE_QUEUE_MAX_QUEUED_PER_PIPELINE` govern runner lifecycle, polling cadence, and queue pressure.

**Follow-ups / nice-to-haves**

- Optional lease heartbeat loop for very long jobs (method is in place, wiring TBD).
- Per-pipeline concurrency quotas and scheduled/cron jobs.
- `/api/engine/jobs/{id}/requeue` convenience helper and richer job logs/metrics streaming.

## Phase 4 — ML Assist Hooks (✅ Implemented)

**Goal**

Offer operator-facing guidance derived from recent Insights data without automatically mutating pipeline specs.

**What shipped**

- Assist service (`engine/ml_assist.py`) surfaces:
  - Allowlist and severity downgrade suggestions for frequent low-signal issues.
  - Anomaly highlights computed via a robust z-score on recent vs. baseline issue rates.
- API endpoints (`POST /api/engine/assist/preview`, `GET /api/engine/assist/anomalies`) expose draft suggestions and anomaly listings for the UI.
- Engine UI Assist card lets operators fetch suggestions, inspect raw allowlist/severity candidates, view anomalies, and insert a commented YAML draft into the editor (no auto-apply).
- Tests (`tests/test_ml_assist_phase4.py`) cover suggestion heuristics and API flows.
- Documentation (this runbook, STATUS, CHANGELOG) updated with Phase 4 deliverables.

**Notes**

- Suggestions are always returned as commented YAML blocks; operators must review and save manually.
- No schema migration required—Assist reads existing `engine_runs`, `engine_messages`, and `engine_issues` tables.

**Follow-ups / nice-to-haves**

- Persisted Assist history per pipeline (compare proposed vs. applied rules).
- Inline diffing against current YAML to show exact impact.
- Export Assist drafts as standalone files for review.

## Phase 5 — Network I/O (MLLP Ingest & Send) (✅ Implemented)

**Goal**

Enable the Engine to **ingest** HL7 v2 via **MLLP** on **specific IP/ports** and to **send** HL7 to configured MLLP targets, managed via API + UI. Inbound traffic becomes background jobs that execute against stored pipelines without requiring YAML edits; outbound delivery is selectable via a named target sink or one-off API call.

**What shipped**

- **Inbound MLLP listeners** bound to **host/IP + port** with **CIDR allowlist** and lightweight back-pressure (job queue).
- **Ingestion jobs** (`kind: "ingest"`) that wrap received bytes in an **inline adapter** and run the attached pipeline.
- **Outbound MLLP targets** (name → host:port), plus a `mllp_target` sink and a **one-off send** API for testing.
- **Endpoint manager** to Start/Stop listeners at runtime.
- **UI Endpoints card** to create inbound/outbound endpoints, manage state, and test sends.
- **Migrations, tests, and docs** to make this production-ready.

**Milestones**

- **5A — Inbound**
  - Migration + model for `engine_endpoints` (inbound/outbound).
  - Async MLLP server (bind host:port, CIDR allowlist).
  - Endpoint manager (start/stop) + API.
  - Runner `kind:"ingest"` override (inline adapter injection).
  - Tests: bind/reject by CIDR, create `ingest` job, end-to-end pipeline execution.

- **5B — Outbound + UI**
  - `mllp_target` sink (resolve named target and deliver).
  - One-off send API (`/api/engine/mllp/send`) with base64 payload.
  - UI Endpoints card (CRUD + start/stop + “send test”).
  - Tests: outbound to mock MLLP echo, UI/API coverage.

**Data model**

- **Table:** `engine_endpoints`
  - `id` (PK), `kind` (`mllp_in` | `mllp_out`), `name` (unique)
  - `pipeline_id` (nullable; required for `mllp_in`)
  - `config` (JSON)
    - For `mllp_in`: `{ "host": "127.0.0.1", "port": 2575, "allow_cidrs": ["127.0.0.1/32"], "timeout": 30 }`
    - For `mllp_out`: `{ "host": "10.0.0.12", "port": 2575 }`
  - `status` (`stopped|starting|running|error`), `last_error`
  - `created_at`, `updated_at`

**Store/API surfaces**

- **Store helpers**
  - `create_endpoint(kind, name, pipeline_id, config) -> EndpointRecord`
  - `update_endpoint(endpoint_id, **fields) -> bool`
  - `delete_endpoint(endpoint_id) -> bool`
  - `get_endpoint(endpoint_id)`, `get_endpoint_by_name(name)`
  - `list_endpoints(kind: list[str] | None) -> list[EndpointRecord]`

- **HTTP API**
  - `POST /api/engine/endpoints` → create inbound/outbound
  - `GET /api/engine/endpoints` → list (optional `?kind=mllp_in|mllp_out`)
  - `GET /api/engine/endpoints/{id}` → detail
  - `POST /api/engine/endpoints/{id}/start` / `stop` → control inbound listener
  - `DELETE /api/engine/endpoints/{id}` → delete endpoint
  - `POST /api/engine/mllp/send` → one-off send: `{target_name? | host+port, message_b64}`

  **Error codes**: 400 invalid input, 404 unknown id/name, 409 bind in use, 422 malformed frame.

**Runtime changes**

- **Inline adapter** (`type: inline`) feeds decoded `message_b64` + optional meta into pipeline without requiring spec edits.
- Runner recognizes `kind:"ingest"` and overlays:
  ```yaml
  adapter:
    type: inline
    config:
      message_b64: "<payload>"
      meta: { peer_ip: "x.x.x.x" }
  ```
- **Endpoint manager** holds active MLLP servers (start/stop), updates `status/last_error`.

**Security**

- **CIDR allowlist is required** for inbound; default deny (no accept unless matched).
- Disallow binding `0.0.0.0` unless explicitly permitted via env (see Config).
- Minimal ACK (AA/AE) to limit info leakage. (Optional future: HL7 MSA templating.)
- All received bytes are treated as **untrusted**; pipelines should validate early (e.g., `validate-hl7` operator).

**Configuration**

- `ENGINE_NET_BIND_ANY` (0/1) – allow `0.0.0.0` binds (default 0)
- `ENGINE_MLLP_READ_TIMEOUT_SECS` (default 30)
- `ENGINE_MLLP_MAX_FRAME_BYTES` (default 1_000_000)
- Reuse Phase 3 runner vars for queue/back-pressure as needed.

**Acceptance criteria**

1. Create inbound endpoint with `host`, `port`, `allow_cidrs`, `pipeline_id`; **start** successfully; second process bind should return **409**.
2. Connections from allowed CIDR are **accepted**, framed HL7 is received, and an **`ingest` job** is enqueued → pipeline runs → Insights updated.
3. Non-allowed client IPs are **rejected** with no job creation.
4. Create outbound target and **send** via:
   - Pipeline `mllp_target` sink, and
   - API `/api/engine/mllp/send`.
5. UI Endpoints card can **create/list/start/stop/delete** endpoints and perform a test send.

**Quick usage examples**

Create inbound & start:
```bash
curl -X POST /api/engine/endpoints -H 'content-type: application/json' \
  -d '{"kind":"mllp_in","name":"adt-in","pipeline_id":3,
       "config":{"host":"127.0.0.1","port":2575,"allow_cidrs":["127.0.0.1/32"]}}'
curl -X POST /api/engine/endpoints/1/start
```

Create outbound target:
```bash
curl -X POST /api/engine/endpoints -H 'content-type: application/json' \
  -d '{"kind":"mllp_out","name":"adt-out","config":{"host":"10.0.0.12","port":2575}}'
```

Send once:
```bash
MSG=$(printf 'MSH|^~\\&|SILHOUETTE|TESTFAC|...\\r' | base64 -w0)
curl -X POST /api/engine/mllp/send -H 'content-type: application/json' \
  -d "{\"target_name\":\"adt-out\",\"message_b64\":\"$MSG\"}"
```

Pipeline sink (YAML):
```yaml
sinks:
  - type: mllp_target
    config:
      target_name: adt-out
```

**Testing plan**

- **Inbound**
  - Start listener; connect from allowed IP; send framed VT…FS CR HL7; expect `ingest` job → `succeeded`.
  - Connect from non-allowed IP; expect close/AE; **no job** created.
  - Bind conflict on second start returns 409.
  - Oversized frame (> `ENGINE_MLLP_MAX_FRAME_BYTES`) returns AE.
- **Outbound**
  - Mock MLLP echo server; send via `/mllp/send` and via `mllp_target` sink; verify ACK and payload reception.
  - Errors (connection refused, timeout) produce job failure + retry (Phase 3 backoff).
- **UI**
  - Form validation; start/stop transitions; errors surfaced in `last_error`.

**Rollout**

- Default: **no endpoints** running. Ops explicitly create and start inbound listeners.
- Autostart can be considered later via an `autostart` flag; not included in this phase to reduce risk.

---

## PR process (Engine/Insights)
1. Update **PHASES.md** (this file) if behaviour/spec/acceptance change
2. Update **STATUS.md** with shipped scope + UTC timestamp
3. Update **CHANGELOG.md** with user-facing notes
4. Ensure tests pass and Quickstart commands above remain valid

---

## Phase 6 — Agent Landing & Orchestrator (Demo) (🚧 In progress)

**Goal**

Provide a single **landing page** that lets an operator either:
- Use a **Chat (beta)** text box to type natural commands that run **without leaving the page**, showing **live confirmations** of exactly what was added and when; or
- Jump to the existing **Engine (manual)** UI.

No external LLM yet; this phase uses a **deterministic parser + orchestrator** to map text → Engine actions. The demo also supports **Generate** and **De-identify** flows against a configured **folder/bucket**.

**What’s included in this phase**

- **Agent API**:  
  - `POST /api/agent/interpret` → map text to `{ intent, params, steps }` (no side effects).  
  - `POST /api/agent/execute` → run the plan; return step-by-step **Execution Report**.  
  - `GET /api/agent/registry` → show supported intents & parameter schemas.  
  - `GET /api/agent/actions` → recent activity log.  
  - `GET /api/agent/actions/stream` → **SSE** for live Activity Timeline.
- **Activity Log**: new `agent_actions` table records intent, params, timestamps, status, and result references (endpoint/job/run ids).
- **Landing page** `/ui/landing`:
  - Chat input with **Preview steps** and **Run**.  
  - **Activity Timeline** (SSE) shows all actions with timestamps and confirmations (**created/started**, **job enqueued**, **run succeeded**).

**6A — Foundations**
- Implement agent actions data model + store helpers.  
- Orchestrator (interpret/execute) with idempotency and safety gates.  
- Landing page (chat + live activity).

**6B — Content skills**
- `generate_messages`: write N HL7 files to `${AGENT_DATA_ROOT}/out/<folder>`.  
- `deidentify_folder`: read `${AGENT_DATA_ROOT}/in/<folder>/**/*.hl7`, run pipeline de-identification, write to `${AGENT_DATA_ROOT}/out/<folder>`.

**6C — Advanced UX**
- Replay & Assist shortcuts in Chat.  
- Better idempotency semantics; wildcard bind enforcement; file root confinement.  
- Richer status badges, links to endpoint/job/run.

**Configuration**
- `AGENT_DATA_ROOT` (default `./data/agent`) — root for generate/deidentify demo.  
- Uses existing Phase 5/3 env vars: `ENGINE_NET_BIND_ANY`, `ENGINE_MLLP_READ_TIMEOUT_SECS`, `ENGINE_MLLP_MAX_FRAME_BYTES`, runner tuning.

**Acceptance**
- Creating a channel (e.g., port **4321**, host **127.0.0.1**) shows **inline confirmation** and appears in the **Activity Timeline** with timestamps (no page navigation).  
- “Generate 10 messages to demo-adt” writes 10 files and logs a summary activity.  
- “De-identify incoming/ward to ward_deid with pipeline 3” processes the folder and logs success/failure counts.  
- All actions callable **headlessly** through APIs.

**Docs**
- See `docs/v2/README-agent.md` for examples and operator notes.
