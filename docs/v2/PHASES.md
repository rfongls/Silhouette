# Engine V2 — Phases & Spec (Single Source of Truth)

**Last updated:** 2025-10-09 (UTC)

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
- `GET /api/engine/health` → `{ ok: true, version: "phase1", feature: "engine-v2" }`
- `GET /api/engine/registry` → registered adapters/operators/sinks
- `POST /api/engine/pipelines/validate` → `{ spec }` or **400** (invalid YAML / unknown components)
- `POST /api/engine/pipelines/run` → `{ run_id?, processed, issues: {error, warning, passed}, spec }`

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

## Phase 2 — Engine UI (🔜 Planned)
- Pipelines list + detail configuration
- Front-end run / dry-run controls (no background runner)
- Insights charts for error/warning/passed trends

## Phase 3 — Background Runner & Replay (🔜 Planned)
- Supervisor, back-pressure, retry policy, dead-letter queue
- Replay pipelines from stored runs

## Phase 4 — ML Assist Hooks (🔜 Planned)
- Allowlist suggestions and anomaly baselines
- UI hints from ML assist results
- Draft config suggestions without auto-apply

---

## PR process (Engine/Insights)
1. Update **PHASES.md** (this file) if behaviour/spec/acceptance change
2. Update **STATUS.md** with shipped scope + UTC timestamp
3. Update **CHANGELOG.md** with user-facing notes
4. Ensure tests pass and Quickstart commands above remain valid
