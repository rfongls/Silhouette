# Entities & Identifiers

- **run_id** — pipeline session ID (one per “Full Pipeline” or user‑chained step run)
- **task_seq** — 1..N order of actions within the run
- **content_id** — versioned HL7 content snapshot produced by a step
- **send_id** — each MLLP send attempt gets a new ID
- **control_id** — HL7 MSH‑10 (enables ACK correlation and search)

**Rule:** Full Pipeline ≡ one `run_id` with multiple `pipeline_task_events`, each pointing to its own `content_id`.
