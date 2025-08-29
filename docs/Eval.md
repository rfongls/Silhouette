# Evaluation (`eval/`)

- Eval runner executes YAML-defined suites against the agent
- Optional containerized build runner for runtime suites

## Commands
```bash
# Run a suite
python -m silhouette_core.cli eval --suite eval/suites/basics.yaml

# Build and run containerized tests
python -m silhouette_core.cli build-runner --suite eval/suites/dev_java_runtime.yaml
```
Suites contain `cases:` with prompts and expected outputs. Results are written to `artifacts/eval_report.json` and can be aggregated via `scripts/scoreboard.py`.
