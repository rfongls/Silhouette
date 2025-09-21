# ADR‑001: Logging Store = SQLite (WAL)

**Decision:** Use SQLite (WAL, FK=ON) + thin access layer.  
**Rationale:** low‑ops, offline‑friendly, portable; fits current scale.  
**Consequences:** 1 writer/many readers; aggregate on read; backups copy `.db` + `-wal`.
