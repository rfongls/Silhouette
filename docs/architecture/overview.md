# Architecture Overview

Silhouette’s Interop analytics use a **thin logging layer over SQLite**:

- **message_versions** — each HL7 “content version” produced by a step
- **pipeline_runs** — a logical session (user or Full Pipeline)
- **pipeline_task_events** — ordered actions within a run (task_seq 1..N)
- **mllp_sends** — every MLLP send attempt (ACK, latency, dest)
- **errors** — non‑task exceptions and diagnostics

Why this works now:
- **Traceable** (ordered steps + lineage)
- **Auditable** (ACK codes, search by MSH‑10)
- **Offline‑first** (SQLite WAL: 1 writer, many readers)
- **Portable** (migrates cleanly to Postgres if/when needed)

UI documents and copy reference our **Skills** & **Interop** prototypes, to keep terminology and call‑to‑actions consistent. 
