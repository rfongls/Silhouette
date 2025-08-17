#!/usr/bin/env bash
set -euo pipefail
python -m training.train_kd --cfg config/train.yaml
STUDENT_MODEL=models/student-core-kd python scripts/eval_report.py
