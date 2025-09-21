# Retry / Re‑queue (MLLP)

Policy:
- Requeue rows with `status='fail'` and `attempts < MAX_ATTEMPTS`
- Optional backoff using `next_retry_utc`

Worker query:
````sql
SELECT * FROM mllp_sends
WHERE status='fail'
  AND (next_retry_utc IS NULL OR next_retry_utc <= strftime('%s','now'))
  AND attempts < 3
ORDER BY sent_at_utc ASC
LIMIT 50;
````

On re‑send:

* success → set `ack_code`, `ack_received_utc`, `status='success'`, `attempts = attempts + 1`
* failure → `attempts = attempts + 1`, set `next_retry_utc`

````
