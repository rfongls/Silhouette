# Operational Runbook

**DB**
- SQLite at `SILHOUETTE_DB` (default: `silhouette_metrics.db`)
- PRAGMAs: WAL, foreign_keys=ON, synchronous=NORMAL
- Backup: copy `.db` (+ `-wal` if hot) or stop app briefly

**Retention (30 days default)**
````sql
DELETE FROM mllp_sends WHERE sent_at_utc < strftime('%s','now') - 2592000;
DELETE FROM pipeline_task_events WHERE created_at_utc < strftime('%s','now') - 2592000;
DELETE FROM message_versions WHERE created_at_utc < strftime('%s','now') - 2592000;
DELETE FROM errors WHERE occurred_at_utc < strftime('%s','now') - 2592000;
````

**Health checks**

* `SELECT 1` on startup
* size threshold alert
* daily write probe (insert+delete)

````
