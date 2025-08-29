# Artifacts

Outputs produced during runs.

## Locations
- `artifacts/hl7/` — HL7 QA reports (CSV/JSONL)
- `artifacts/selfcheck.json` — self-check summary
- `artifacts/eval_report.json` — evaluation results
- `artifacts/latency/latency.json` — latency probe metrics
- `artifacts/scoreboard/index.html` — HTML dashboard aggregated from reports
- `artifacts/security_report.json` — license/secret scan findings

## .gitignore
Add `artifacts/` to `.gitignore` to keep outputs out of VCS.
