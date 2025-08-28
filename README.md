# 🌑 Silhouette Core

**Silhouette Core** is a survivable, modular, and scalable AI agent framework.  
It is purpose-aligned, hardware-flexible, and built to be **carried, revived, and evolved** across any environment — even when modern infrastructure is unavailable.

---

## 🌐 Vision

Silhouette Core is a **general, self-hostable agent system**. It is designed to:

* Operate offline or in constrained environments.  
* Learn and refine skills across multiple ecosystems (Python, Java, .NET, Android, Web, C++).  
* Support compliance and provenance (license scanning, redaction, watermarking, licensing).  
* Continuously improve itself through **training → evaluation → distillation → redeployment**.  
* Distill large models into **small, survivable agents** that can run on the edge.  

Language runtimes are **capability modules** the agent can exercise.  
Silhouette Core itself is **not an app** — it is the engine that demonstrates how agents can persist, replicate, and evolve safely.

---

## 🎯 Purpose

Silhouette Core is a **general, self-hostable agent framework**. Its purpose is to:

- Operate safely in **offline or constrained environments**.  
- Support **training, distillation, and quantization** so large models can be distilled into small, task-focused agents.  
- Evaluate itself across **multiple programming ecosystems** (Python, Java, .NET, Android, Web, C++).  
- Learn continuously through a **data flywheel**: runtime evals → traces → training.  
- Provide **skills** (tools, wrappers) the agent can ingest dynamically.  
- Enforce **compliance and provenance**: redaction, license scanning, watermarks, customer licensing.  

---

## 🛠 End Goal

The end state (Phase 10) is a **production-ready agent system** that can:

- **Generate, compile, and test** code across languages in isolated containers (Python, Web, Java, .NET, Android, C++).  
- **Train itself** on successes via curated KD traces.  
- **Run on edge devices** via quantized exports (<3s latency on CPU).  
- **Provide governance** through licensing, watermarking, and compliance gates.  
- Be packaged, released, and licensed as a **trustworthy, cross-language development agent**.

---

## 🔍 What It Does (Current Features)

* **Alignment-first agent loop**: persona DSL config (`persona.dsl`), deny rules, self-check.  
* **Memory & context**: logs interactions, replays into structured memory JSONL.  
* **Skills system**: dynamic tool registry (`skills/registry.yaml`), versioned (`name@vN`).  
* **Runtime evals**: cross-language build/test inside Docker (Java, .NET, Android, Web, Python, C++).  
* **Linters**: Python (ruff, black), Web/JS (eslint), C++ (clang-tidy optional).  
* **Offline-first mode**: deterministic stub generation when models are unavailable.
* **Training adapters**: SFT + KD wrappers (student models distilled from teacher traces).
* **Research Toolpack (offline)**: read PDF → index (SQLite FTS5) → search/retrieve → cite [n]. Requires citations for research prompts.
* **Cybersecurity Toolpack**: authorized scans & audits — Nmap (host/top-1000), OWASP ZAP baseline, Trivy (image/fs), Checkov (IaC), CIS local checks, CVE lookup; scope-guarded & containerized.
* **Cybersecurity Reference Pack**: CDSE/NIST checklists and references mapped to findings, plus task orchestration that produces cited assessment reports.
* **Interoperability Toolkit**: HL7 v2, C-CDA, and X12 translators with mock connectors, validators, and end-to-end tests.
* **Data Flywheel v2**: runtime traces auto-promoted to curated datasets by lane.
* **Compliance**: SPDX license scan, redaction rules, configurable thresholds.
* **Regression gates**: enforce pass-rate thresholds and latency budgets in CI.
* **Provenance**: WATERMARK.json in every artifact with repo commit + SHA256.
* **Self-replication**: export profiles, distill knowledge, quantize models, package clones.
* **Release governance**: structured release pipeline with attached compliance and provenance artifacts.
* **Customer licensing**: issue per-customer license files and embed IDs into WATERMARK.json.

### Interoperability at a glance

Ready-made diagrams cover HL7 v2 ↔ FHIR mapping, TEFCA/QHIN flows, IHE XDS.b exchanges, Direct Secure Messaging, SMART on FHIR authorization, prior authorization (FHIR + X12), MDM entity resolution, and HIE record locator queries. See [docs/interoperability](docs/interoperability/).

---

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
````

---

## ⚙️ Install & CLI

Dev install:

```bash
pip install -e .[all]
```

Run:

```bash
silhouette run --profile profiles/core/policy.yaml
silhouette eval --suite eval/suites/basics.yaml
silhouette build-runner --suite eval/suites/dev_java_runtime_ext.yaml
silhouette train --mode sft --cfg config/train.yaml
silhouette selfcheck --policy profiles/core/policy.yaml
silhouette package --out dist/
silhouette quantize --method int8 --src models/student-core-kd --out models/student-core-int8
SILHOUETTE_EDGE=1 STUDENT_MODEL=models/student-core-int8 silhouette latency
silhouette license --customer-id ORG-1234
```

---

## 🧪 Running Evaluations

Basics:

```bash
silhouette eval --suite eval/suites/basics.yaml
```

Developer stacks:

```bash
silhouette eval --suite eval/suites/dev_python.yaml
silhouette eval --suite eval/suites/dev_java.yaml
silhouette eval --suite eval/suites/dev_dotnet_runtime.yaml
```

Runtime (compile/run in Docker):

```bash
ENABLE_RUNTIME_EVAL=1 silhouette build-runner --suite eval/suites/dev_java_runtime_ext.yaml
ENABLE_RUNTIME_EVAL=1 silhouette build-runner --suite eval/suites/dev_dotnet_runtime_ext.yaml
ENABLE_RUNTIME_EVAL=1 silhouette build-runner --suite eval/suites/dev_android_runtime_ext.yaml
ENABLE_RUNTIME_EVAL=1 silhouette build-runner --suite eval/suites/dev_web_runtime.yaml
ENABLE_RUNTIME_EVAL=1 silhouette build-runner --suite eval/suites/dev_python_runtime.yaml
ENABLE_RUNTIME_EVAL=1 silhouette build-runner --suite eval/suites/dev_cpp_runtime.yaml
```

---

## 🧠 Training & Data Flywheel

Passing runtime evals are logged into lane-specific buckets:

```bash
silhouette eval --suite eval/suites/basics.yaml
```

Developer stacks:

```bash
silhouette eval --suite eval/suites/dev_python.yaml
silhouette eval --suite eval/suites/dev_java.yaml
silhouette eval --suite eval/suites/dev_dotnet_runtime.yaml
```

Curate and deduplicate:

```bash
ENABLE_RUNTIME_EVAL=1 silhouette build-runner --suite eval/suites/dev_java_runtime_ext.yaml
ENABLE_RUNTIME_EVAL=1 silhouette build-runner --suite eval/suites/dev_dotnet_runtime_ext.yaml
ENABLE_RUNTIME_EVAL=1 silhouette build-runner --suite eval/suites/dev_android_runtime_ext.yaml
ENABLE_RUNTIME_EVAL=1 silhouette build-runner --suite eval/suites/dev_web_runtime.yaml
ENABLE_RUNTIME_EVAL=1 silhouette build-runner --suite eval/suites/dev_python_runtime.yaml
ENABLE_RUNTIME_EVAL=1 silhouette build-runner --suite eval/suites/dev_python_fastapi_runtime.yaml
ENABLE_RUNTIME_EVAL=1 silhouette build-runner --suite eval/suites/dev_python_ml_runtime.yaml
ENABLE_RUNTIME_EVAL=1 silhouette build-runner --suite eval/suites/dev_skill_runtime.yaml
```

Probe latency in edge mode:

```bash
SILHOUETTE_EDGE=1 STUDENT_MODEL=models/student-core-int8 silhouette latency
```

Reports to `artifacts/latency/latency.json`.

---

## 🛡 Security & Compliance

* **SPDX license scanning** with whitelist/denylist.
* **Redaction rules** for logs and traces.
* **Regression gates** enforce lane pass rates + latency budgets.
* See [COMPLIANCE.md](COMPLIANCE.md).

---

## 🔐 Licensing & Watermarks

* **Proprietary LICENSE**: no training/fine-tuning/redistribution without contract.
* **CUSTOMER\_LICENSE\_TEMPLATE.md**: rendered by `scripts/issue_customer_license.py`.
* **Customer licensing**:

  ```bash
  silhouette license --customer-id ORG-1234
  ```

  Produces `artifacts/licenses/license_ORG-1234_<date>.md` and updates WATERMARK.json.
* **WATERMARK.json**: includes provenance (commit, SHA256, license tag, customer ID).

### Customer Licensing

Issue a license and embed provenance:

```bash
silhouette license --customer-id ORG-1234
```

### Customer Licensing

Issue a license and embed provenance:

```bash
silhouette license --customer-id ORG-1234
```

### Customer Licensing

Issue a license and embed provenance:

```bash
silhouette license --customer-id ORG-1234
```
Outputs:

* `artifacts/licenses/license_ORG-1234_<date>.md` (rendered contract)
* Updates `WATERMARK.json` with customer_id + license_date

---

## 📊 Scoreboards & Gates

Run and build:

```bash
python scripts/scoreboard.py
python scripts/scoreboard_history.py
python scripts/regression_gate.py --report artifacts/scoreboard/latest.json --previous artifacts/scoreboard/previous.json
```

Artifacts:

* `artifacts/scoreboard/index.html` (latest)
* `artifacts/scoreboard/phase-N.html` (snapshot)
* `artifacts/scoreboard/history.html` (trend dashboard)
* `artifacts/gates/gate_summary.json` (regression gate status)

---

## 🛣 Roadmap (Phases)

| Phase | PRs     | Focus                                       |
| ----- | ------- | ------------------------------------------- |
| 1–3   | 1–3     | Core agent hardening                        |
| 2     | 4–5     | Training foundation                         |
| 3     | 6–9     | Distillation & quantization                 |
| 4     | 10–11.2 | Profiles + evals                            |
| 5     | 12–14   | Skills & dataset flywheel v1                |
| 6     | 15–18   | Compliance & provenance                     |
| 7     | 19–21   | Cross-language expansion (Web, Python, C++) |
| 8     | 22–23   | Continuous improvement (traces, gates)      |
| 9     | 24–25   | Packaging & edge deployment                 |
| 10    | 26–27   | Release & licensing                         |

---

## 🐙 GitHub Issue Automation

Seed the next development phase's GitHub issues from a local YAML file:

```bash
python scripts/create_github_issues.py --repo <owner>/<repo> --token $GITHUB_TOKEN --dry-run
```

Remove `--dry-run` to create the issues.

## 📚 Additional Docs

- [Installer quickstart](docs/INSTALL_QUICKSTART.md)
- [Repo integration guide](docs/repo_integration.md)
- [HL7 testing guide](docs/hl7_testing.md)
- [Offline parity workflow](docs/offline_parity.md)
- [Release candidate checklist](docs/rc_checklist.md)
- [Codex handoff](docs/codex_handoff.md)
- [Docs index](docs/README.md)

---

## 🚀 Release & Licensing

Silhouette Core uses a structured release pipeline:
- Version bump in `pyproject.toml` + tag push.
- CI builds and runs regression gates.
- Artifacts are attached to GitHub release (wheel, scoreboard, compliance, watermark).
- See [RELEASE.md](RELEASE.md) for full checklist.

---

### HL7 Draft & Send — Web UI (with presets)

1. Start the MLLP server (or point to a partner endpoint).
   ```bash
   python -m interfaces.hl7.mllp_server
   ```

2. Start the web app:

   ```bash
   uvicorn server:app --reload --port 8080
   ```

3. Open [http://localhost:8080/ui/hl7](http://localhost:8080/ui/hl7)

   * Pick a message type (VXU, RDE, ORM, OML, ORU:RAD, MDM, ADT, SIU, DFT)
   * Click **Load Example for Selected Type** to prefill JSON
   * Edit as needed → **Draft** or **Draft & Send** (sends via MLLP; shows ACK)

Targets in `config/hosts.yaml` populate the host/port dropdown.

### Agentic LLM Smoke (local vLLM/Ollama)

1) Start the HL7 listener (MLLP) and your OpenAI-compatible server:
   ```bash
   python -m interfaces.hl7.mllp_server &
   # vLLM example:
   vllm serve meta-llama/Meta-Llama-3-8B-Instruct --download-dir ./model_vault --port 8000 &
   # (Ollama OpenAI-compatible: set OPENAI_API_BASE=http://localhost:11434/v1 and choose your model)
   ```

2. Run the smoke:

   ```bash
   python scripts/agent_llm_smoke.py \
     --base http://localhost:8000/v1 \
     --model meta-llama/Meta-Llama-3-8B-Instruct \
     --host 127.0.0.1 --port 2575 \
     --message "Send a VXU for John Doe (CVX 208) to localhost:2575 and summarize the ACK."
```

If your model supports Tools API, it will return a tool call; otherwise it may emit a JSON fallback the script understands. On success you’ll see a short summary and an ACK (look for `MSA|AA|...`).

## HL7 QA Validator — Usage & Commands

Validate HL7 v2 messages against site-tunable **profiles** defined in `rules.yaml`.
The validator supports two engines:

* **fast** — raw ER7 parsing (no object tree): *HL7Spy-like speed* (default via `rules.yaml`).
* **hl7apy** — full object model: use when you need strict grammar/group reasoning.

You can set the engine per profile in `rules.yaml` or override at the CLI.

### Table of Contents

1. [Prerequisites](#prerequisites)
2. [Folder Layout](#folder-layout)
3. [Configure Rules](#configure-rules)

   * [Profiles & Engines](#profiles--engines)
   * [Timestamp Policy](#timestamp-policy)
   * [Allowed Values & Policies](#allowed-values--policies)
4. [Run the App](#run-the-app)

   * [Windows (cmd)](#windows-cmd)
   * [Windows (PowerShell)](#windows-powershell)
   * [macOS/Linux (bash/zsh)](#macoslinux-bashzsh)
   * [Useful Variants](#useful-variants)
5. [CLI Options Reference](#cli-options-reference)
6. [Artifacts & Version Control](#artifacts--version-control)
7. [Troubleshooting & Performance](#troubleshooting--performance)
8. [Ready-Made Scripts](#ready-made-scripts)

### Prerequisites

* **Python** ≥ 3.10
* **Dependencies**

  * Install with:

    * **Windows (cmd/PowerShell)**

      ```bat
      py -m pip install -U pip
      py -m pip install -r requirements.txt
      ```
    * **macOS/Linux**

      ```bash
      python3 -m pip install -U pip
      python3 -m pip install -r requirements.txt
      ```
  * `hl7apy` is **optional** unless you use `--engine hl7apy` (or a profile sets `engine: hl7apy`).

Create an output folder:

* **Windows**

  ```bat
  mkdir artifacts\hl7 2>nul
  ```
* **macOS/Linux**

  ```bash
  mkdir -p artifacts/hl7
  ```

### Folder Layout

```
repo/
  tools/
    hl7_qa.py                 # the validator
  tests/
    fixtures/hl7/             # sample HL7 files (inputs)
    hl7/rules/rules.yaml      # profile-based validation rules (site-tunable)
  artifacts/
    hl7/                      # CSV/JSONL reports (outputs; safe to .gitignore)
```

### Configure Rules

#### Profiles & Engines

`rules.yaml` selects a profile by the **root** of `MSH-9` (e.g., `ORU` from `ORU^R01`).
Each profile may include:

* `engine: fast | hl7apy` — choose the engine for that profile (optional; defaults to `fast`).
* `types: [...]` — list of root message types matched by this profile.

Example:

```yaml
profiles:
  oru_results:
    engine: fast
    types: [ORU]
  adt_messages:
    engine: fast
    types: [ADT]
default_profile: oru_results
```

You can override at runtime via `--engine fast|hl7apy|auto` (see [CLI Options](#cli-options-reference)).

#### Timestamp Policy

Control how TS fields are validated:

```yaml
timestamps:
  mode: length_only        # 'length_only' | 'calendar' | 'off'
  strict: true             # if invalid, register as error (with fail_on_dtm)
  fail_on_dtm: true        # treat invalid TS as value_error (else warning)
  allowed_lengths: [8, 12, 14]   # YYYYMMDD, YYYYMMDDHHMM, YYYYMMDDHHMMSS
  compliant_lengths: [8, 12, 14] # lengths considered “compliant”
  fields:
    - "MSH-7"  # message datetime
    - "OBR-7"  # observation datetime
    - "OBX-14" # observation datetime (result)
```

* `length_only` (default): accept **numeric** TS with allowed base lengths (fraction/timezone syntax allowed).
* `calendar`: additionally verify calendar ranges (valid month/day/time).
* `off`: skip TS checks.

> Your current policy is `length_only` with allowed lengths 8/12/14.

#### Allowed Values & Policies

Profiles can include *allowed values* (e.g., `result_status`, `encounter_class`) and *policies*:

```yaml
allowed:
  result_status: [F, C, I, P, R, S, U, D, X, W]
  obx11_empty_allows: [X, I, W, U]
  encounter_class: [E, I, O, P, R, B, C, N, U]   # ADT PV1-2

policies:
  require_pid3_shape: true
  require_obr2_or_obr3: true
  obr4_coded: true
  obr25_allowed: true
  obx11_allowed: true
  obx3_coded: true
  obx5_required_unless_status_in_empty_allows: true
  obx2_vs_obx5_typecheck: true
  require_pv1_2_encounter_class: true
  required_fields:
    - "PID-3.1"
    - "PID-5.1"
    - "PID-8"
```

> See your `rules.yaml` for full examples (ORU/ORM/OML/MDM/ADT/RDE/VXU/SIU).

### Run the App

> Replace the input with your HL7 file if needed: `tests\fixtures\hl7\sample_set_x.hl7`

#### Windows (cmd)

**Fast engine (recommended for throughput)**

```bat
py -X utf8 tools\hl7_qa.py "tests\fixtures\hl7\sample_set_x.hl7" --rules "tests\hl7\rules\rules.yaml" --engine fast --progress-every 200 --progress-time 10 --max-errors-per-msg 10 --max-print 0 --report "artifacts\hl7\sample_set_x_fast.csv"
```

**HL7apy engine (full object model)**

```bat
py -X utf8 tools\hl7_qa.py "tests\fixtures\hl7\sample_set_x.hl7" --rules "tests\hl7\rules\rules.yaml" --engine hl7apy --hl7apy-validation none --workers auto --chunk 200 --progress-every 200 --progress-time 10 --max-errors-per-msg 10 --max-print 0 --report "artifacts\hl7\sample_set_x_hl7apy.csv"
```

> **cmd multiline tip:** paste the entire block at once; **no spaces** after `^`.
> If you see `More?`, cmd is waiting for the rest of the line.

#### Windows (PowerShell)

**Fast**

```powershell
py -X utf8 tools/hl7_qa.py "tests/fixtures/hl7/sample_set_x.hl7" `
  --rules "tests/hl7/rules/rules.yaml" `
  --engine fast `
  --progress-every 200 --progress-time 10 `
  --max-errors-per-msg 10 --max-print 0 `
  --report "artifacts/hl7/sample_set_x_fast.csv"
```

**HL7apy**

```powershell
py -X utf8 tools/hl7_qa.py "tests/fixtures/hl7/sample_set_x.hl7" `
  --rules "tests/hl7/rules/rules.yaml" `
  --engine hl7apy --hl7apy-validation none `
  --workers auto --chunk 200 `
  --progress-every 200 --progress-time 10 `
  --max-errors-per-msg 10 --max-print 0 `
  --report "artifacts/hl7/sample_set_x_hl7apy.csv"
```

#### macOS/Linux (bash/zsh)

**Fast**

```bash
python3 tools/hl7_qa.py tests/fixtures/hl7/sample_set_x.hl7 \
  --rules tests/hl7/rules/rules.yaml \
  --engine fast \
  --progress-every 200 --progress-time 10 \
  --max-errors-per-msg 10 --max-print 0 \
  --report artifacts/hl7/sample_set_x_fast.csv
```

**HL7apy**

```bash
python3 tools/hl7_qa.py tests/fixtures/hl7/sample_set_x.hl7 \
  --rules tests/hl7/rules/rules.yaml \
  --engine hl7apy --hl7apy-validation none \
  --workers auto --chunk 200 \
  --progress-every 200 --progress-time 10 \
  --max-errors-per-msg 10 --max-print 0 \
  --report artifacts/hl7/sample_set_x_hl7apy.csv
```

### Useful Variants

**Process a subset (fast iteration)**

```bat
py -X utf8 tools\hl7_qa.py "tests\fixtures\hl7\sample_set_x.hl7" --rules "tests\hl7\rules\rules.yaml" --engine fast --start 1000 --limit 500 --max-errors-per-msg 10 --max-print 0 --report "artifacts\hl7\sample_set_x_1k-1.5k.csv"
```

**Filter to specific message types (e.g., ORU_R01 & ADT_A01)**

```bat
py -X utf8 tools\hl7_qa.py "tests\fixtures\hl7\sample_set_x.hl7" --rules "tests\hl7\rules\rules.yaml" --engine fast --only ORU_R01,ADT_A01 --max-errors-per-msg 10 --max-print 0 --report "artifacts\hl7\oru_adt_check.csv"
```

**Write JSONL instead of CSV (one JSON object per line)**

```bat
py -X utf8 tools\hl7_qa.py "tests\fixtures\hl7\sample_set_x.hl7" --rules "tests\hl7\rules\rules.yaml" --engine fast --max-errors-per-msg 10 --max-print 0 --report "artifacts\hl7\sample_set_x.jsonl"
```

**Parallel (best with hl7apy engine)**

```bat
py -X utf8 tools\hl7_qa.py "tests\fixtures\hl7\sample_set_x.hl7" --rules "tests\hl7\rules\rules.yaml" --engine hl7apy --hl7apy-validation none --workers auto --chunk 250 --progress-every 200 --progress-time 10 --max-errors-per-msg 10 --max-print 0 --report "artifacts\hl7\sample_set_x_parallel.csv"
```

### CLI Options Reference

* `--engine auto|fast|hl7apy`
  `auto` uses `profile.engine` (or **fast** if unset). Override per run.
* `--hl7apy-validation none|tolerant|strict`
  Only used when `engine=hl7apy`. `none` recommended (YAML drives TS).
* `--no-quiet-parse`
  Show hl7apy logs/warnings (default is suppressed).
* `--report <path>`
  Output **.csv** or **.jsonl** by extension.
* `--progress-every N` / `--progress-time S`
  Print progress every N messages / at least every S seconds.
* `--start N` / `--limit N`
  Skip first N messages / process at most N.
* `--only TYPE[,TYPE...]`
  Include only certain `MSH-9` types (e.g., `ORU_R01,ADT_A01`).
* `--max-errors-per-msg N`
  Cap stored errors per message (default 50).
* `--max-print N`
  Cap console prints per message (default 3).
* `--workers auto|N` / `--chunk N`
  Parallelize across processes (most effective with `hl7apy`).

### Artifacts & Version Control

Reports are written under `artifacts/hl7/`. Keep outputs out of git:

```
# .gitignore
artifacts/
```

You can move `artifacts/` under a different directory (e.g., `hl7/artifacts/`) — just adjust `--report` paths in your commands.

### Troubleshooting & Performance

* **Only 1 message processed:** your file was treated as one giant message. The splitter now matches message starts at `\A` or after `\r`/`\n` and accepts **any** field separator byte after `MSH`. If you still see 1 msg, check your source (zipped/wrapped).
* **It feels “hung” on start:** for very large files, reading and scanning anchors happens before the first progress line. Use `--progress-time 10` to ensure periodic updates.
* **hl7apy is slow on some messages:** that’s normal on big/odd structures. Use `--engine fast` for volume QA and switch to `hl7apy` only when you need structural validation.
* **TS values rejected by hl7apy:** TS acceptance is driven by **your YAML** (`timestamps.mode`). We parse with hl7apy **without** TS enforcement and apply your policy instead.
* **Windows caret (`^`) pitfalls:** paste the whole block at once; no spaces after `^`. If you see `More?`, cmd is mid-line.

### Ready-Made Scripts

#### `run_examples.bat` (Windows cmd)

```bat
@echo off
setlocal
if not exist artifacts\hl7 mkdir artifacts\hl7

REM Fast engine (recommended)
py -X utf8 tools\hl7_qa.py "tests\fixtures\hl7\sample_set_x.hl7" ^
  --rules "tests\hl7\rules\rules.yaml" ^
  --engine fast ^
  --progress-every 200 --progress-time 10 ^
  --max-errors-per-msg 10 --max-print 0 ^
  --report "artifacts\hl7\sample_set_x_fast.csv"

REM HL7apy engine (object model)
py -X utf8 tools\hl7_qa.py "tests\fixtures\hl7\sample_set_x.hl7" ^
  --rules "tests\hl7\rules\rules.yaml" ^
  --engine hl7apy --hl7apy-validation none ^
  --workers auto --chunk 200 ^
  --progress-every 200 --progress-time 10 ^
  --max-errors-per-msg 10 --max-print 0 ^
  --report "artifacts\hl7\sample_set_x_hl7apy.csv"

REM Subset run (quick iteration)
py -X utf8 tools\hl7_qa.py "tests\fixtures\hl7\sample_set_x.hl7" ^
  --rules "tests\hl7\rules\rules.yaml" ^
  --engine fast ^
  --start 1000 --limit 500 ^
  --max-errors-per-msg 10 --max-print 0 ^
  --report "artifacts\hl7\sample_set_x_1k-1.5k.csv"
```

#### `run_examples.ps1` (PowerShell)

```powershell
New-Item -ItemType Directory -Force -Path artifacts\hl7 | Out-Null

# Fast engine
py -X utf8 tools/hl7_qa.py "tests/fixtures/hl7/sample_set_x.hl7" `
  --rules "tests/hl7/rules/rules.yaml" `
  --engine fast `
  --progress-every 200 --progress-time 10 `
  --max-errors-per-msg 10 --max-print 0 `
  --report "artifacts/hl7/sample_set_x_fast.csv"

# HL7apy engine
py -X utf8 tools/hl7_qa.py "tests/fixtures/hl7/sample_set_x.hl7" `
  --rules "tests/hl7/rules/rules.yaml" `
  --engine hl7apy --hl7apy-validation none `
  --workers auto --chunk 200 `
  --progress-every 200 --progress-time 10 `
  --max-errors-per-msg 10 --max-print 0 `
  --report "artifacts/hl7/sample_set_x_hl7apy.csv"

# Subset run
py -X utf8 tools/hl7_qa.py "tests/fixtures/hl7/sample_set_x.hl7" `
  --rules "tests/hl7/rules/rules.yaml" `
  --engine fast `
  --start 1000 --limit 500 `
  --max-errors-per-msg 10 --max-print 0 `
  --report "artifacts/hl7/sample_set_x_1k-1.5k.csv"
```

### Codex-Driven Tests

- **On push/PR**: CI runs unit + E2E tests, builds the Profile Conformance report, and exports Mermaid diagrams.
- **On demand**: Comment `/codex test` on any PR to re-run tests and artifact generation.
- **Nightly (optional)**: A daily E2E subset runs on `main`. Enable/disable in `.github/workflows/nightly-e2e.yml`.

Artifacts (audit logs, conformance report, SVG diagrams) are attached to each workflow run under “Artifacts”.

## 📜 License

Silhouette Core is **proprietary**.
No training, fine-tuning, or redistribution without a written agreement.
See [`LICENSE`](LICENSE).
