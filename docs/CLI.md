# Silhouette CLI (`silhouette_core/cli.py`)

## Overview
Unified command-line interface for Silhouette Core operations.

## Installation
```bash
python -m pip install -r requirements.txt
```

## Usage
```bash
python -m silhouette_core.cli <command> [options]
```

## Commands

| Command | Description | Key Options |
|---------|-------------|-------------|
| `repo map` | Build a repository map for a source tree | `--json-out`, `--html-out`, `--no-html`, `--compute-hashes` |
| `run` | Start the interactive agent REPL | `--profile PATH`, `--student-model PATH`, `--offline` |
| `eval` | Run evaluation suite | `--suite PATH`, `--require_runtime_env` |
| `build-runner` | Execute containerized compile/test suite | `--suite PATH`, `--require-runtime-env` |
| `synth-traces` | Convert runtime passes into KD traces | `--lane NAME` (repeatable) |
| `train` | Train student via SFT or KD | `--cfg PATH`, `--mode sft|kd` |
| `selfcheck` | Run policy and tool self-check | `--policy PATH` |
| `package` | Build wheel/sdist artifacts | `--out DIR` |
| `quantize` | Export or quantize a student model | `--method int8|gguf|onnx-int8`, `--src`, `--out` |
| `latency` | Measure model latency | *(no options)* |
| `license` | Issue customer license and watermark | `--customer-id`, `--out DIR` |
| `analyze hotpaths` | Rank files by call graph centrality | `--json` |
| `analyze service` | Trace dependencies for a module | `--json` |
| `suggest tests` | Suggest tests for a path | `--json` |
| `summarize ci` | Summarize CI results | `--json` |
| `propose patch` | Generate a policy-filtered patch proposal | `--goal`, `--hint`, `--strategy` |

## Examples

```bash
# Start the agent REPL with the default profile
python -m silhouette_core.cli run

# Map this repository and render HTML
python -m silhouette_core.cli repo map . --html-out repo.html

# Train from config using KD mode
python -m silhouette_core.cli train --cfg config/train.yaml --mode kd

# Quantize a trained model to int8
python -m silhouette_core.cli quantize --method int8 --src models/student-core-kd --out artifacts/int8
```
