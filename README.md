# 🌑 Silhouette Core

**Silhouette Core** is a survivable, modular, and scalable AI agent framework.  
It is purpose-aligned, hardware-flexible, and built to be **carried, revived, and evolved** across any environment — even when modern infrastructure is unavailable.

> **Docs Index:** See [docs/README.md](docs/README.md) for the full table of contents.
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

### 🔍 What It Does (Current Features)

- **Alignment-first agent loop** — [Agents](docs/Agents.md) · [Agent API](docs/agent_api.md) · [Profiles (persona DSL)](docs/Profiles.md)
- **Memory & context** — [Artifacts & logs](docs/Artifacts.md) · [User Guide](docs/User_Guide.md) · [Codex Handoff](docs/codex_handoff.md)
- **Skills system** — [Skills](docs/Skills.md) · [Skills Catalog](docs/skills_catalog.md) · [Agent API](docs/agent_api.md)
- **Runtime evals** — [Eval Guide](docs/Eval.md) · [CLI](docs/CLI.md)
- **Linters** — [Contributing (linting/workflow)](docs/contributing.md) · [Install Quickstart](docs/INSTALL_QUICKSTART.md) · [Repo Integration](docs/repo_integration.md)
- **Offline-first mode** — [Offline Mode](docs/Offline_Mode.md)
- **Training adapters (SFT + KD)** — [Training](docs/Training.md) · [Knowledge Distillation](docs/Knowledge_Distillation.md) · [Manual Training Guide](docs/manual_training_guide.md)
- **Research Toolpack (offline)** — [Research Toolpack](docs/research_toolpack.md) · [Skills Catalog](docs/skills_catalog.md)
- **Cybersecurity Toolpack** — [Cyber Toolpack](docs/cyber_toolpack.md) · [Persona Guide](docs/persona-guide.md)
- **Cybersecurity Reference Pack** — [RC Checklist](docs/rc_checklist.md) · [Skills Catalog](docs/skills_catalog.md)
- **Interoperability Toolkit** — [HL7 Testing Runbook](docs/hl7_testing.md) · [Interop Overview](docs/interoperability/overview.md)
- **Data Flywheel v2** — [PHASES (roadmap)](docs/PHASES.md) · [Manual Training Guide](docs/manual_training_guide.md)
- **Compliance** — [Security / Redaction / PII](docs/Security.md) · [API Index](docs/API.md)
- **Regression gates** — [Monitoring & SLOs](docs/monitoring.md) · [PHASES](docs/PHASES.md)
- **Provenance** — [Security (provenance notes)](docs/Security.md) · [README (release artifacts)](docs/README.md)
- **Self-replication** — [Package Clone](docs/Package_Clone.md) · [Quantization](docs/Quantization.md)
- **Release governance** — [Deploy Guide](docs/deploy-guide.md) · [CHANGELOG](CHANGELOG.md) · [PHASES](docs/PHASES.md)
- **Customer licensing** — [Security](docs/Security.md) · [PHASES](docs/PHASES.md)

### Interoperability at a glance

Ready-made diagrams cover HL7 v2 ↔ FHIR mapping, TEFCA/QHIN flows, IHE XDS.b exchanges, Direct Secure Messaging, SMART on FHIR authorization, prior authorization (FHIR + X12), MDM entity resolution, and HIE record locator queries. See [docs/interoperability](docs/interoperability/).

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
├── docs/PHASES.md              # Phase-by-phase breakdown
├── MILESTONES.md               # PR-by-PR milestones
└── README.md                   # This file
