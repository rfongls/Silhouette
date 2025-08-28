# 🌑 Silhouette Core

> **Docs Index:** See [docs/README.md](docs/README.md) for the full table of contents.

## 📂 Project Structure

```text
Silhouette/
├── cli/                        # Legacy REPL
├── silhouette_core/            # Core library + new CLI
│   ├── cli.py                  # Unified `silhouette` CLI
│   ├── agent_controller.py     # Spawn/fork/merge agents
│   ├── offline_mode.py         # Safe-mode & throttling
│   ├── distiller.py            # Knowledge distillation
│   ├── quantize_models.py      # Quantization routines
│   └── package_clone.py        # Build deployable clone archive
├── eval/                       # Eval runner & suites
├── scripts/                    # Utilities
│   ├── scoreboard.py
│   ├── scoreboard_history.py
│   ├── regression_gate.py
│   ├── synthesize_traces.py
│   ├── promote_traces.py
│   ├── quantize.py
│   ├── latency_probe.py
│   ├── watermark_artifact.py
│   ├── verify_watermark.py
│   └── issue_customer_license.py
├── training/                   # SFT/KD adapters
├── skills/                     # Skills registry + versioned skills
├── profiles/                   # Policy YAMLs
├── security/                   # License scanner + redaction
├── artifacts/                  # Scoreboards, latency logs, traces
├── config/                     # Gates, train, lanes
├── docs/                       # Guides & philosophy
├── RELEASE.md                  # Release playbook
├── CHANGELOG.md                # Changelog
├── LICENSE                     # Proprietary license
├── COMPLIANCE.md               # Compliance policy
├── CUSTOMER_LICENSE_TEMPLATE.md# Customer license template
├── PHASES.md                   # Phase-by-phase breakdown
├── MILESTONES.md               # PR-by-PR milestones
└── README.md                   # This file
```

## ⚡ HL7 QA — Quick Start

- **All run commands:** [docs/hl7_testing.md](docs/hl7_testing.md)
- **Windows CMD (fast engine example):**
  ```bat
  py -X utf8 tools\hl7_qa.py "tests\fixtures\hl7\sample_set_x.hl7" --rules "tests\hl7\rules\rules.yaml" --engine fast --progress-every 200 --progress-time 10 --max-errors-per-msg 10 --max-print 0 --report "artifacts\hl7\sample_set_x_fast.csv"
  ```
- **Windows CMD (hl7apy engine example):**
  ```bat
  py -X utf8 tools\hl7_qa.py "tests\fixtures\hl7\sample_set_x.hl7" --rules "tests\hl7\rules\rules.yaml" --engine hl7apy --hl7apy-validation none --workers auto --chunk 200 --progress-every 200 --progress-time 10 --max-errors-per-msg 10 --max-print 0 --report "artifacts\hl7\sample_set_x_hl7apy.csv"
  ```
