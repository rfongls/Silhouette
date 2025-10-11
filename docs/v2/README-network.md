# Network I/O (MLLP) Operator Guide

> **Status:** Planned for Phase 5 — the workflow below reflects the intended UX once the Network I/O work ships. Use this as a runbook to prepare infra, credentials, and validation tooling ahead of rollout.

## Quickstart

1. **Create an inbound listener**
   ```bash
   curl -X POST /api/engine/endpoints \
        -H 'content-type: application/json' \
        -d '{
              "kind": "mllp_in",
              "name": "adt-in",
              "pipeline_id": 42,
              "config": {
                "host": "127.0.0.1",
                "port": 2575,
                "allow_cidrs": ["127.0.0.1/32"],
                "timeout": 30
              }
            }'
   curl -X POST /api/engine/endpoints/ID/start
   ```
   Replace `ID` with the numeric identifier returned by the create call. The listener will refuse connections from IPs outside the `allow_cidrs` list.

2. **Register an outbound target**
   ```bash
   curl -X POST /api/engine/endpoints \
        -H 'content-type: application/json' \
        -d '{
              "kind": "mllp_out",
              "name": "adt-out",
              "config": {
                "host": "10.0.0.12",
                "port": 2575
              }
            }'
   ```

3. **Send a one-off test message**
   ```bash
   MSG=$(printf 'MSH|^~\&|SILHOUETTE|CORE|TEST|SITE|202501011200||ADT^A01|0001|P|2.5\rPID|1||12345^^^SILHOUETTE^MR\r' | base64 -w0)
   curl -X POST /api/engine/mllp/send \
        -H 'content-type: application/json' \
        -d "{\"target_name\":\"adt-out\",\"message_b64\":\"$MSG\"}"
   ```
   The response includes an `ack_preview` field with the first 32 bytes of the received ACK payload.

4. **Wire a pipeline sink**
   ```yaml
   sinks:
     - type: mllp_target
       config:
         target_name: adt-out
   ```
   Any pipeline that produces HL7 bytes can re-use the target without exposing credentials or host details in YAML.

## UI workflow

The Engine → **Endpoints** card will offer:

- Creation dialogs for inbound listeners and outbound targets.
- Status badges showing `stopped`, `starting`, `running`, or `error`.
- Buttons to **Start** / **Stop** inbound listeners.
- A "Send test message" drawer that accepts raw HL7 (auto-encoded to base64) and either a target name or ad-hoc host:port.
- Inline surfacing of the latest `last_error` message when a listener fails to bind.

## Troubleshooting

| Symptom | Checks & Fixes |
|---------|----------------|
| `409 Conflict` on `.../start` | Another process is already bound to the requested host:port. Stop the other listener or pick a new port. |
| Immediate connection close with no ACK | The client IP is not inside `allow_cidrs`. Update the allowlist and restart the listener. |
| ACK body is `AE` | The server rejected the frame (timeout, oversize, or enqueue failure). Inspect the Engine logs for `mllp.handler.error` entries. |
| `400 Bad Request` during create | Ensure `mllp_in` endpoints include `pipeline_id`, `allow_cidrs`, and a non-wildcard `host` unless `ENGINE_NET_BIND_ANY=1`. |
| Listener shows `error` status | Check `last_error` via `GET /api/engine/endpoints/{id}`. Common causes are bind conflicts, invalid CIDR strings, or timeouts waiting on the job queue. |
| Frames larger than expected | The maximum frame size is capped by `ENGINE_MLLP_MAX_FRAME_BYTES` (default 1 MiB). Increase the env var and restart the process if you must accept larger payloads. |
| Slow ACK turnaround | Tune `ENGINE_MLLP_READ_TIMEOUT_SECS` (default 30). High latency networks may require a larger timeout to avoid AE responses. |

## Operational tips

- Keep listeners behind a TCP load balancer if you need horizontal scale; designate a single Engine instance as the "ingress" host to avoid duplicate processing.
- Log every inbound connection (peer IP + pipeline) during the pilot phase to validate allowlists before widening CIDRs.
- For outbound routing, configure downstream ACK expectations (AA vs. CA) and alerting on repeated AE responses.
- Maintain an inventory of ports in use to avoid conflicting with other services (consider reserving a dedicated range, e.g., 2500–2520).
- Rotate credentials (if any) and monitor disk usage for queued ingest jobs—the queue will provide back-pressure if downstream pipelines slow down.

## Glossary

- **AA** — Application Accept (success ACK)
- **AE** — Application Error (non-fatal failure)
- **AR** — Application Reject (fatal failure; treated as AE for retries)
- **VT/FS/CR** — Start/End framing bytes used by MLLP (`0x0b`, `0x1c`, `0x0d`)

