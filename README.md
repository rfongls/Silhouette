Excellent — I can see the full project structure in the uploaded repo.

Here’s the plan to **fix your README.md**:

* Keep **all the detailed functionality** you already had (CLI usage, directory structure, training flow, eval suites).
* Add back the **Vision / Purpose / End Goal** (based on all PRs through Phase 10).
* Update the **Project Structure** and usage details to reflect what’s actually in the repo now (`eval/`, `training/`, `scripts/`, `skills/`, etc.).
* Make sure **compliance, watermarking, licensing** from PR-17/18 are present.
* Include the **roadmap phases** summary (so README matches `phases.md`).

---

# Updated `README.md` (full, integrated)

````markdown
# 🌑 Silhouette Core

**Silhouette Core** is a survivable, modular, and scalable AI agent framework.  
It is purpose-aligned, hardware-flexible, and built to be **carried, revived, and evolved** across any environment — even when modern infrastructure is unavailable.

---

## 🌐 Vision

Silhouette Core is a **general, self-hostable agent system**. It is designed to:

Language runtimes (Python, Java, .NET, Android, Web, C++) are **capability modules** the agent can exercise.
Silhouette Core itself is **not an app** — it is the engine that demonstrates how agents can persist, replicate, and evolve safely.

* Operate offline or in constrained environments.  
* Learn and refine skills across multiple ecosystems (Python, Java, .NET, Android, Web, C++).  
* Support compliance and provenance (license scanning, redaction, watermarking, licensing).  
* Continuously improve itself through **training → evaluation → distillation → redeployment**.  
* Distill large models into **small, survivable agents** that can run on the edge.  

---

## Purpose

Silhouette Core is a **general, self-hostable agent framework**. Its purpose is to:

- Operate safely in **offline or constrained environments**.  
- Support **training, distillation, and quantization** so large models can be distilled into small, task-focused agents.  
- Evaluate itself across **multiple programming ecosystems** (Python, Java, .NET, Android, Web, C++).  
- Learn continuously through a **data flywheel**: runtime evals → traces → training.  
- Provide **skills** (tools, wrappers) the agent can ingest dynamically.  
- Enforce **compliance and provenance**: redaction, license scanning, watermarks, customer licensing.  

## End Goal

The end state (Phase 10) is a **production-ready agent system** that can:

- **Generate, compile, and test** code across languages in isolated containers.  
- **Train itself** on successes via curated KD traces.  
- **Run on edge devices** via quantized exports.  
- **Provide governance** through licensing, watermarking, compliance gates.  
- Be packaged, released, and licensed as a **trustworthy, cross-language development agent**.

Silhouette Core is not “an Android app” — it is an **agent engine** that demonstrates how large models can be broken down into resilient, specialized modules that survive infrastructure collapse while still providing advanced capabilities.

At **Phase 10**, Silhouette Core will deliver:

* **Cross-language agent capabilities** (Python, Web, Java, .NET, Android, C++).  
* **Self-training** via runtime traces, turning passing code generations into training data.  
* **Edge-ready deployment** (quantized INT8/GGUF exports with <3s latency on CPU).  
* **Governed artifacts** (every model watermarked, licensed, and verifiable).  
* **Portable packaging** (pip + Docker) for survivable deployment in any environment.  

---

## 🔍 What It Does (Current Features)

* **Alignment-first agent loop**: persona DSL config (`persona.dsl`), deny rules, self-check.  
* **Memory & context**: logs interactions, replays into structured memory JSONL.  
* **Skills system**: dynamic tool registry (`skills/registry.yaml`), versioned (`name@vN`).  
* **Runtime evals**: cross-language build/test inside Docker (Java, .NET, Android).  
* **Offline-first mode**: deterministic stub generation when models are unavailable.  
* **Training adapters**: SFT + KD wrappers (student models distilled from teacher traces).  
* **Compliance**: SPDX license scan, redaction rules, configurable thresholds.  
* **Provenance**: WATERMARK.json in every artifact with repo commit + SHA256.  
* **Self-replication**: export profiles, distill knowledge, quantize models, package clones.  

---

## 📂 Project Structure

```text
Silhouette/
├── cli/                        # CLI entrypoint & REPL commands
│   └── main.py
├── silhouette_core/            # Core agent + loop
│   ├── agent_controller.py     # Spawn/fork/merge agents
│   ├── agent_messaging.py      # Inter-agent messaging
│   ├── offline_mode.py         # Safe-mode & throttling
│   ├── drift_detector.py       # Tone/intent drift analysis
│   ├── persona_audit.py        # Persona compliance checks
│   ├── distiller.py            # Knowledge distillation
│   ├── quantize_models.py      # Model quantization
│   └── package_clone.py        # Build deployable clone archive
├── eval/                       # Eval runner & suites
│   ├── eval.py                 # Eval harness
│   ├── build_runner.py         # Runtime compile/run wrapper
│   └── suites/                 # Eval suites (basics, dev stacks, runtime)
├── scripts/                    # Utilities
│   ├── scoreboard.py           # HTML scoreboard generator
│   ├── scoreboard_history.py   # History dashboard
│   ├── watermark_artifact.py   # Write WATERMARK.json
│   ├── verify_watermark.py     # Check WATERMARK.json
│   └── synthesize_traces.py    # Convert runtime passes into KD traces
├── training/                   # Training adapters
│   ├── train_sft.py            # Supervised fine-tuning
│   ├── train_kd.py             # Knowledge distillation
│   └── adapters/               # File-fence, LoRA, etc.
├── skills/                     # Dynamic tools/skills
│   ├── registry.yaml           # Declares active skills
│   └── http_get_json/v1/...    # Example skill (versioned)
├── config/                     # Config for training, performance, drift
├── docs/                       # Guides & philosophy
│   ├── HANDOFF_GUIDE.md
│   ├── self_replication.md
│   ├── contributing.md
│   ├── philosophy.md
│   └── roadmap.md
├── tests/                      # Unit & integration tests
├── LICENSE                     # Proprietary license
├── COMPLIANCE.md               # Compliance policy & scanner usage
├── CUSTOMER_LICENSE_TEMPLATE.md# Contract template for customers
├── PHASES.md                   # Phase-by-phase breakdown
├── MILESTONES.md               # PR-by-PR milestones
└── README.md                   # This file
````

---

## ⚙️ Usage Guide

### CLI Quickstart

```bash
python -m cli.main
```

**Key commands:**

* `:modules` → list skills
* `:selfcheck` → run policy checks
* `:export-profile` → export persona/memory/modules profile
* `:distill` → run distillation
* `:agent spawn/fork/merge` → manage agents
* `:backup` / `:restore` → encrypted state mgmt

---

## 🧪 Running Evaluations

Basics:

```bash
python -m eval.eval --suite eval/suites/basics.yaml
```

Developer stacks:

```bash
python -m eval.eval --suite eval/suites/dev_python.yaml
python -m eval.eval --suite eval/suites/dev_java.yaml
python -m eval.eval --suite eval/suites/dev_dotnet_runtime.yaml
```

Runtime (compile/run in Docker):

```bash
ENABLE_RUNTIME_EVAL=1 python -m eval.build_runner --suite eval/suites/dev_java_runtime_ext.yaml
ENABLE_RUNTIME_EVAL=1 python -m eval.build_runner --suite eval/suites/dev_dotnet_runtime_ext.yaml
ENABLE_RUNTIME_EVAL=1 python -m eval.build_runner --suite eval/suites/dev_android_runtime_ext.yaml
```

---

## 🛡 Security & Compliance

* **SPDX license scanning** with whitelist/denylist.
* **Redaction rules** for logs and traces.
* **Thresholds**: fail if blocked license (GPL, AGPL, MPL) or >N medium findings.
* See [COMPLIANCE.md](COMPLIANCE.md).

---

## 🔐 Licensing & Watermarks

* **Proprietary LICENSE**: no training/fine-tuning/redistribution without a contract.
* **CUSTOMER\_LICENSE\_TEMPLATE.md**: contract template for client licenses.
* **WATERMARK.json**: every model artifact includes provenance (commit, SHA256, license tag, optional customer ID).

Verify:

```bash
python scripts/verify_watermark.py --artifact_dir models/student-core-kd
```

---

## 📊 Scoreboards

Run evals, then build HTML reports:

```bash
python scripts/scoreboard.py
PHASE=phase-6 python scripts/scoreboard.py
python scripts/scoreboard_history.py
```

Artifacts:

* `artifacts/scoreboard/index.html` (latest)
* `artifacts/scoreboard/phase-N.html` (per-phase snapshot)
* `artifacts/scoreboard/history.html` (trend dashboard)

---

## 🛣 Roadmap (Phases)

**Phase 1–3**: Core Agent + Training Foundation
**Phase 4–5**: Policy, Evals, Skills, Dataset Flywheel v1
**Phase 6**: Compliance & Provenance (security, watermarking, licensing)
**Phase 7**: Cross-Language Expansion (Web, Python, C++)
**Phase 8**: Continuous Improvement (auto-trace promotion, regression gates)
**Phase 9**: Packaging & Edge Deployment (pip, GGUF, ONNX)
**Phase 10**: Release & Licensing (release playbook, customer licensing, watermark issuance)

See [PHASES.md](PHASES.md) for details.

---

## 📜 License

Silhouette Core is **proprietary**.
No training, fine-tuning, or redistribution without a written agreement.
See [`LICENSE`](LICENSE).

```

Would you like me to also **auto-generate a one-page “at-a-glance roadmap graphic”** (a markdown table or ASCII flow) for the README so new readers immediately see the 10 phases?
```