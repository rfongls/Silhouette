# SQLite Schema (DDL) & ER

Silhouette uses one SQLite file (default: `silhouette_metrics.db`), initialized at app start.

## ER (ASCII)

```

pipeline\_runs(run\_id PK)
1 ──< pipeline\_task\_events(event\_id PK, run\_id FK, content\_id FK)
|
v
message\_versions(content\_id PK, parent\_id FK)

pipeline\_runs(run\_id)
1 ──< mllp\_sends(send\_id PK, run\_id FK, content\_id FK)

errors(event\_id FK?, run\_id FK?) ──> references for rich diagnostics

```

## Tables

### message_versions
- `content_id` (uuid, PK)
- `parent_id` (FK to message_versions.content_id, nullable)
- `stage` (`generate|deid|validate|translate|…`)
- `hl7_type`, `hl7_version`, `control_id` (MSH‑10)
- `created_at_utc` (epoch seconds)
- `message_text` (full HL7 content)

### pipeline_runs
- `run_id` (uuid, PK), `started_at_utc`, `trigger` (`user|full_pipeline|api`)
- `status` (`running|success|fail`), `note`

### pipeline_task_events
- `event_id` (PK), `run_id` (FK), `task_seq` (1..N)
- `action` (`generate|deid|validate|translate|mllp`)
- `content_id` (FK), `status` (`success|fail`), `elapsed_ms`
- `created_at_utc`, `error_code`, `error_message`
- `details_json` (compact JSON: counts, top_errors, etc.)

### mllp_sends
- `send_id` (uuid, PK), `run_id` (FK), `content_id` (FK)
- `control_id` (MSH‑10), `sent_at_utc`
- `dest_ip`, `dest_port`, `message_text`
- `ack_code`, `ack_received_utc`, `ack_payload`
- `status` (`queued|success|fail`), `attempts`, `next_retry_utc`, `error_message`

### errors
- `id` (PK), `occurred_at_utc`, `severity` (`error|warn|info`)
- `component` (`mllp|validate|deid|translate|app`)
- `run_id` (FK), `event_id` (FK), `code`, `message`, `payload_json`
