# Pipeline Run Semantics

- A **run** starts on Full Pipeline or when a user begins chaining steps.
- Each step logs a **task event** with monotonically increasing **task_seq**.
- Steps that produce content persist a **message_version** (`content_id`) with optional `parent_id` for lineage.

**Universal UI rule:** clicking any pipeline card collapses other panels and expands the target (chips reflect `active`). This mirrors the Interop prototype’s single‑focus flow. :contentReference[oaicite:5]{index=5}
