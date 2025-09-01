# Cybersecurity Skill Phases 6–10

## Safety & Guardrails

- **Authorization required** for pentest commands: pass `--ack-authorized` at the `security` CLI group.
- **Scope enforcement**: targets must appear in a scope file (see `docs/cyber/scope_example.txt`).
- **Offline-first**: no network calls; all outputs are produced locally under `out/security/<UTC_ISO>/...`.

### Pentest Gate Environment Controls

| Variable                | Example                 | Effect |
|------------------------|-------------------------|--------|
| `CYBER_KILL_SWITCH`    | `true`                  | Deny all pentest actions globally. |
| `CYBER_DENY_LIST`      | `/path/deny.txt`        | newline list of denied targets. |
| `CYBER_PENTEST_WINDOW` | `09:00-17:00`           | **UTC** window for allow; deny outside window. |
| `CYBER_THROTTLE_SECONDS` | `300`                 | Enforce min seconds between runs. |
| `CYBER_ALLOWLIST`      | `/path/allow.txt`       | newline list of “owned/approved” targets. |
| `CYBER_DNS_DIR`        | `/path/dns_proofs/`     | `<target>.txt` = DNS TXT proof stub. |
| `CYBER_HTTP_DIR`       | `/path/http_proofs/`    | `<target>.txt` = HTTP proof stub. |

> ⏱️ **Time windows are UTC**. `CYBER_PENTEST_WINDOW=09:00-17:00` is compared against `datetime.utcnow()`.
> Convert your local window to UTC when setting this value.
