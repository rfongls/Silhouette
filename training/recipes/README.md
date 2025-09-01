# Training Recipes (Scaffold)

This directory explains how to plug datasets into Silhouette Core
*without* committing to any domain.

## Adapters
Implement `training/adapters/<name>_adapter.py` that subclasses `BaseAdapter`
and yields dicts like:
```json
{"instruction": "...", "input": "...", "output": "...", "tools_used": ["calc"]}
```

## Running Training

```bash
python -m training.train_sft --cfg config/train.yaml
python -m training.train_kd  --cfg config/train.yaml
```

## Next Steps

* Add export/quantization for CPU/edge
* Expand eval suites for focused agents

