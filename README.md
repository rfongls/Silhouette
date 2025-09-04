# 🌑 Silhouette Core

**Silhouette Core** is a survivable, modular, and scalable AI agent framework.  
It is purpose-aligned, hardware-flexible, and built to be **carried, revived, and evolved** across any environment — even when modern infrastructure is unavailable.

> **Docs Index:** See [docs/README.md](docs/README.md) for the full table of contents.
---

## 🚀 One-Click Agent Setup

- Windows: double-click `setup.bat`
- macOS: double-click `setup.command`
- Linux/macOS terminal: `./setup.sh`

Non-interactive example:

```bash
python setup.py --skill fhir --with-hapi --yes
```

| Skill | Extras |
|-------|--------|
| core | *(none)* |
| runtime | `[runtime]` |
| ml | `[ml]` |
| dev | `[dev]` |
| eval | `[eval]` |
| validate | `[validate]` |
| fhir | `[fhir]` |
| all | `[runtime,ml,dev,eval,validate,fhir]` |

For more details see [docs/ops/agent_setup.md](docs/ops/agent_setup.md).

## 🖥️ UI Quickstart
### One-click
- **Windows**: double-click `scripts/run_ui.bat`
- **macOS**: double-click `scripts/run_ui.command` (first time only, you may need to run `chmod +x scripts/run_ui.command`)

These will:
1) Create `.venv` (if missing)
2) Install minimal UI deps
3) Launch the server and open your browser at:
   - http://localhost:8000/ui/security/dashboard
   - http://localhost:8000/ui/interop/dashboard

### Manual
Launch the dashboards locally:

```bash
uvicorn main:app --reload
```

Then visit:

- http://localhost:8000/ui/security/dashboard
- http://localhost:8000/ui/interop/dashboard
- http://localhost:8000/ui/security/seeds
- http://localhost:8000/ui/security/safety

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


* **Alignment-first agent loop** – persona DSL config (`persona.dsl`), deny rules, self-check. See [Agents](docs/Agents.md).
* **Memory & context** – logs interactions, replays into structured memory JSONL.
* **Skills system** – dynamic tool registry (`skills/registry.yaml`), versioned (`name@vN`). See [Skills](docs/Skills.md).
* **Runtime evals** – cross-language build/test inside Docker (Java, .NET, Android, Web, Python, C++). See [Eval](docs/Eval.md).
* **Linters** – Python (ruff, black), Web/JS (eslint), C++ (clang-tidy optional).
* **Offline-first mode** – deterministic stub generation when models are unavailable. See [Offline Mode](docs/Offline_Mode.md).
* **Training adapters** – SFT + KD wrappers (student models distilled from teacher traces). See [Training](docs/Training.md) and [Knowledge Distillation](docs/Knowledge_Distillation.md).
* **Research Toolpack (offline)** – read PDF → index (SQLite FTS5) → search/retrieve → cite [n]. Requires citations for research prompts.
* **Cybersecurity Toolpack** – authorized scans & audits — Nmap (host/top-1000), OWASP ZAP baseline, Trivy (image/fs), Checkov (IaC), CIS local checks, CVE lookup; scope-guarded & containerized.
* **Cybersecurity Reference Pack** – CDSE/NIST checklists and references mapped to findings, plus task orchestration that produces cited assessment reports.
* **Interoperability Toolkit** – HL7 v2, C-CDA, and X12 translators with mock connectors, validators, and end-to-end tests. See [HL7 skill docs](docs/skills/hl7/).
* **Data Flywheel v2** – runtime traces auto-promoted to curated datasets by lane.
* **Compliance** – SPDX license scan, redaction rules, configurable thresholds. See [Security](docs/Security.md).
* **Regression gates** – enforce pass-rate thresholds and latency budgets in CI. See [Eval](docs/Eval.md).
* **Provenance** – WATERMARK.json in every artifact with repo commit + SHA256. See [Security](docs/Security.md).
* **Self-replication** – export profiles, distill knowledge, quantize models, package clones. See [Knowledge Distillation](docs/Knowledge_Distillation.md), [Quantization](docs/Quantization.md), and [Package Clone](docs/Package_Clone.md).
* **Release governance** – structured release pipeline with attached compliance and provenance artifacts.
* **Customer licensing** – issue per-customer license files and embed IDs into WATERMARK.json. See [Security](docs/Security.md).

### Interoperability at a glance

Ready-made diagrams cover HL7 v2 ↔ FHIR mapping, TEFCA/QHIN flows, IHE XDS.b exchanges, Direct Secure Messaging, SMART on FHIR authorization, prior authorization (FHIR + X12), MDM entity resolution, and HIE record locator queries. See [docs/interoperability](docs/interoperability/).


## Using the HL7 & FHIR skills
- [HL7 QA](docs/skills/hl7/)
- [FHIR translator](docs/skills/fhir/)
- [HL7⇄FHIR workflows](docs/skills/workflows/hl7_fhir_workflows.md)

### Install (editable)

```bash
pip install -e .

# Include validation extras for `silhouette fhir validate`
pip install -e .[validate]
```

## HL7 v2 → FHIR CLI Examples

Translate an HL7 message to FHIR without posting it:

```bash
silhouette fhir translate \
  --in tests/data/hl7/adt_a01.hl7 \
  --map maps/adt_uscore.yaml \
  --bundle transaction \
  --out out/ \
  --dry-run
```

Validate the generated resources against US Core using the HAPI validator:

```bash
# Option A: quoted literal glob (PowerShell requires quotes)
silhouette fhir validate \
  --in 'out/fhir/ndjson/*.ndjson' \
  --hapi

# Option B: directory of NDJSON files
silhouette fhir validate \
  --in-dir out/fhir/ndjson \
  --hapi
```

Post a bundle to a FHIR server with server-side `$validate`:

```bash
silhouette fhir translate \
  --in tests/data/hl7/adt_a01.hl7 \
  --map maps/adt_uscore.yaml \
  --bundle transaction \
  --out out/ \
  --server https://example.com/fhir \
  --token $FHIR_TOKEN \
  --validate
```

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

