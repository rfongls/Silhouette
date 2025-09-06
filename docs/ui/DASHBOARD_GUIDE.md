# Silhouette Dashboards — Plug-and-Play Guide

This guide shows how to use the **Security** and **Interoperability** dashboards with zero setup beyond one-click launch.

## Security
**Goal:** quick baseline + insights.
1) **Quick Start → Run Baseline** — enter a target (e.g., `example.com`) to run **Gate ➜ Recon (safe)** and see a summary table
2) **KPIs** update instantly (Gate, Recon services/hosts/ports + CVEs/KEV + severities, Netforensics)
3) **Load Demo** populates KPIs offline if no target is available
4) Tools:
   - **Gate** — verifies scope/authorization
   - **Recon** — discovery scan (`safe`, `version`, `full`), with streaming
   - **Netforensics** — upload `.pcap`; summary shows packets/flows/alerts
   - **IR Playbook** — choose a scenario (e.g., ransomware) for steps/schedule

Artifacts: `out/security/**/active/*.json`
Config/Seeds: `config/security.env`, `data/security/seeds/**`

## Interoperability
**Goal:** HL7 ➜ FHIR pipeline in one click.
1) **Quick Start → Run Pipeline** — choose a trigger (e.g., `VXU_V04`)
   Draft HL7 ➜ Translate ➜ Validate (no listener required)
2) **KPIs** update instantly: Send(ACK), Translate OK/Fail, Validate OK/Fail
3) **Draft & Send** — choose an **Example** to auto-fill valid JSON; or download a sample `.hl7`
4) **Translate / Validate** — upload files and view structured results

Artifacts: `out/interop/**/active/*.json`
Examples: `static/examples/hl7/…`, `static/examples/interop/results/…`, `static/examples/fhir/bundle.json`

## How KPIs & trends work
KPIs summarize the latest artifacts under `out/**/active/*.json`.
Tiny trend indices are persisted to:
```
out/security/ui/index.json
out/interop/ui/index.json
```
and used to render simple sparklines on History pages.

## Troubleshooting
- **No ACK?** Ensure a listener is running, or use Quick Start (no listener needed).
- **Empty KPIs?** Click **Load Demo**.
- **Windows paths:** ensure `out/` isn’t read-only.

