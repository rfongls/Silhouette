# Manual Training Guide

This guide walks through the data flywheel used to train Silhouette models.

## 1. Collect Runtime Traces

Run evals so the agent generates code and tests. Successful runs produce trace
JSONL files.

```bash
python scripts/synthesize_traces.py
```

Traces are stored under `training_data/flywheel/<lane>/runtime.jsonl`.

## 2. Promote Curated Traces

Review and promote useful traces into lane-specific datasets:

```bash
python scripts/promote_traces.py --lane python
```

Curated files are written next to the runtime traces.

## 3. Train

Use the unified CLI wrappers for SFT or KD runs:

```bash
silhouette train --mode sft --cfg config/train.yaml
silhouette train --mode kd  --cfg config/train.yaml
```

Models are written to `models/<name>/`.

## 4. Quantize and Probe Latency

```bash
silhouette quantize --method int8 --src models/student-core-kd --out models/student-core-int8
SILHOUETTE_EDGE=1 STUDENT_MODEL=models/student-core-int8 silhouette latency
```

Latency results are saved to `artifacts/latency/latency.json`.
