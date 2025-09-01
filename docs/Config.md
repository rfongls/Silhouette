# Configuration (`config/`)

Central YAML files that tune training, evaluation, and runtime behavior.

## Files
- `default.yaml` – base defaults consumed by the CLI and scripts
- `distillation.yml` – settings for `distiller.py` (e.g., summary length, quantization bits)
- `gates.yaml` – lane pass-rate thresholds and latency budgets
- `lanes.yaml` – ordered list of eval lanes
- `routes.yaml` – connector or service routing rules
- `train.yaml` / `train_config.yaml` / `train_weighting.yaml` – training recipes
- `drift.yml`, `hosts.yaml`, `performance.yml` – environment/host parameters
