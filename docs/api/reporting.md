# Reporting API (Validate & ACKs)

Two reporting surfaces:

- **Validate** (by `pipeline_task_events` where `action='validate'`):
  - Summary (totals, success rate, avg latency)
  - Search (filter by text in `details_json`, by window)
- **ACKs** (by `mllp_sends`):
  - Filters: `ack_code`, `status`, `control_id`, `since`
  - Computed field: ACK latency = `ack_received_utc - sent_at_utc`

> If existing `/api/metrics/validate_*` endpoints are already in use, keep them; otherwise, port to `/api/audit/*`. Both patterns are documented for continuity with current UI. :contentReference[oaicite:4]{index=4}
