# Monitoring

Silhouette tracks evaluation results and regressions to keep the agent honest.

## Scoreboard

Generate HTML and JSON summaries of eval results:

```bash
python scripts/scoreboard.py
python scripts/scoreboard_history.py
```

Artifacts:
- `artifacts/scoreboard/index.html`
- `artifacts/scoreboard/history.html`
- `artifacts/scoreboard/latest.json`

## Regression Gates

Compare the latest scores with a previous snapshot. CI fails if pass rates or
latency exceed configured budgets.

```bash
python scripts/regression_gate.py --report artifacts/scoreboard/latest.json --previous artifacts/scoreboard/previous.json
```

Summary is written to `artifacts/gates/gate_summary.json`.

## Latency Probe

Edge mode can measure on-device latency for a quantized model:

```bash
SILHOUETTE_EDGE=1 STUDENT_MODEL=models/student-core-int8 silhouette latency
```

The probe writes `artifacts/latency/latency.json`.
