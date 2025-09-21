# MLLP ACKs Reporting

**What we log**
- One row per attempt in `mllp_sends`
- On ACK: `ack_code`, `ack_received_utc`, optional `ack_payload`

**Filters**
- `ack_code` (AA/AE/AR), `status`, `control_id` (MSH‑10), `since`
- Show ACK latency = `ack_received_utc - sent_at_utc`

**UI**
- Search form + table, rows link back into Interop (MLLP/FHIR)
- Consistent with the Skills/Interop tokens and layout. :contentReference[oaicite:7]{index=7}
```
