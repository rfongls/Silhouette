# Audit API

Base path: `/api/audit`

## WRITE endpoints

**Start a run**  
POST `/run/start` → `{ "run_id": "uuid" }`  
Body: `{ "trigger": "user|full_pipeline|api", "note": "optional" }`

**Finish a run**  
POST `/run/finish` → `{ "ok": true }`  
Body: `{ "run_id": "uuid", "status": "success|fail" }`

**Save message version**  
POST `/message` → `{ "content_id": "uuid" }`  
Body fields: `stage`, `message_text`, optional `hl7_type`, `hl7_version`, `control_id`, `parent_id`

**Log task event**  
POST `/task` → `{ "event_id": 123 }`  
Fields: `run_id`, `action`, `content_id`, `status`, `elapsed_ms?`, `error_*?`, `details?`

**MLLP send**  
POST `/mllp/send` → `{ "send_id":"uuid" }`  
Fields: `run_id?`, `content_id`, `control_id?`, `dest_ip`, `dest_port`, `message_text`, `status?`

**MLLP ack**  
POST `/mllp/ack` → `{ "ok": true }`  
Fields: `send_id`, `ack_code`, `ack_payload?`, `status?`

**Error**  
POST `/error` → `{ "ok": true }`  
Fields: `component`, `message`, `severity?`, `run_id?`, `event_id?`, `code?`, `payload?`

## READ endpoints

**Recent activity**  
GET `/activity/recent?limit=20` → `[{ created_at_utc, action, status, task_seq, run_id, hl7_type, hl7_version }]`

**ACK search**  
GET `/mllp/search?ack_code=AA&control_id=...&status=success&since=86400&limit=100`
