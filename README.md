# 🌑 Silhouette Core

**Silhouette Core** is a survivable, modular, and scalable AI agent framework.
It is purpose-aligned, hardware-flexible, and built to be **carried, revived, and evolved** across any environment — even when modern infrastructure is unavailable.

> **Docs Index:** See [docs/README.md](docs/README.md) for the full table of contents.

---

## Engine V2 (Beta) — Current Status

> Looking for the original V1 delivery plan? See the repository-root [PHASES.md](PHASES.md)
> (labeled **Legacy**) for historical context. All current Engine work lives under `docs/v2/`.

The Engine V2 runtime (adapters/operators/router/sinks) is being delivered in phases.

- **Current completed phases:** Phase 0 (Skeleton), Phase 0.5 (Demo run + registry)
- **Next phase:** Phase 1 (Adapters & Operators: wire V1 validations and de-identify)
- **Docs:** Single source of truth: **[docs/v2/PHASES.md](docs/v2/PHASES.md)**  
  (See also: [STATUS.md](docs/v2/STATUS.md) and [CHANGELOG.md](docs/v2/CHANGELOG.md))

Quickstart for Engine V2 (Beta):

```bash
(cd insights/migrations && alembic upgrade head)
python -m insights.store seed
make engine-dev
```

---

## UI & Dashboards

 Silhouette Core separates **Reports** (KPI summaries) from **Skills** (dashboards with tools).

 - **Reports Home**: `/ui/home` — shows KPI cards for all enabled skills and includes a Quick Launch dropdown to jump straight to a skill dashboard.
 - **Skills Index**: `/ui/skills` — navigate to each skill’s dashboard.
 - **Registry**: `config/skills.yaml` toggles which skills appear and where their summary/dashboard routes live.

See **[docs/ui_skills_registry.md](docs/ui_skills_registry.md)** for the full architecture and how to add new skills.

> Existing skills:
> - Interoperability — `/ui/interop/dashboard`
> - Security — `/ui/security/dashboard`

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
- **Linux**: double-click `scripts/run_ui.sh` in your file manager (or run `bash scripts/run_ui.sh`). First time only: `chmod +x scripts/run_ui.sh`

- **Direct Engine V2 launcher**: run `run.engine.bat` (Command Prompt) or `run.engine.ps1` (PowerShell) to set `ENGINE_V2=1`, apply sensible defaults for `INSIGHTS_DB_URL` / `AGENT_DATA_ROOT`, and start `uvicorn server:app --reload --host 127.0.0.1 --port 8000`.

These launchers now enable **Engine V2 + Agent landing** automatically:
1) Create `.venv` (if missing)
2) Install minimal UI deps
3) Launch Uvicorn with `ENGINE_V2=1`
4) Open your browser at:
   - http://localhost:8000/ui/landing (Agent chat + live activity timeline)
   - http://localhost:8000/ui/engine (Engine beta dashboard)
   - http://localhost:8000/ui/security/dashboard and http://localhost:8000/ui/interop/dashboard (classic dashboards)

### Manual
Launch the dashboards locally:

```bash
ENGINE_V2=1 uvicorn server:app --reload
```

Optional helpers for the Agent demo flows:

```bash
export AGENT_DATA_ROOT=./data/agent
export INSIGHTS_DB_URL="sqlite:///data/insights.db"
```

### Start Menu shortcuts (Windows)
- `scripts\install_shortcuts.bat` — installs Start Menu entries without requiring PowerShell.
- `scripts\uninstall_shortcuts.bat` — removes the Start Menu folder the installer creates (supports `--dry-run`, `--both`, etc.).
- `make install-shortcuts` / `make uninstall-shortcuts` — automation-friendly wrappers.
- `python scripts/install_shortcuts.py --dry-run` — preview what will be created or pass `--start-menu-path` for a custom location.

The installer creates launchers for the classic UI, the Engine V2 dev server, and handy browser links (Landing + Agent README).

### What you’ll see (plug-and-play)
Both dashboards open with **KPI bars** and **Quick Start** so a new user can click → run → see insights immediately.

**Security Dashboard**
- **KPI bar**: Gate allowed/total, Recon services/hosts/ports + CVEs/KEV + severity buckets, Netforensics alerts/packets
- **Quick Start — Baseline**: one-click **Gate ➜ Recon (safe)** with a readable summary table
- **Load Demo**: copies offline sample results into `out/security/ui/demo/active` so KPIs populate without a real target

**Interoperability Dashboard**
- **KPI bar**: Send (ACK pass/fail), Translate OK/Fail, Validate OK/Fail
- **Quick Start — Pipeline**: Draft example HL7 ➜ FHIR Translate ➜ Validate (no external listener required)
- **Load Demo**: seeds Interop KPIs with example results

**Where artifacts go**
- Security: `out/security/**/active/*.json`
- Interop: `out/interop/**/active/*.json`

**Examples**
- HL7 (downloadable): `static/examples/hl7/samples/*.hl7`
- HL7 (drafter JSON): `static/examples/hl7/json/*.json`
- FHIR bundle: `static/examples/fhir/bundle.json`
- Interop demo results: `static/examples/interop/results/*.json`
- Security demo results: `static/examples/cyber/results/*.json`

> KPIs auto-refresh every 10s; actions also push small **out-of-band** fragments that refresh KPIs instantly.

### Quick smoke tests (fast)
After the code changes, run:
```bash
pytest -q tests/test_interop_kpi.py tests/test_security_kpi.py
```
These seed tiny dummy artifacts, hit the summary endpoints, and confirm `index.json` trend files are written.

> Tip: If you want `/` to land on the UI, apply the small `RedirectResponse` tweak shown earlier.
Then visit:

- http://localhost:8000/ui/security/dashboard
- http://localhost:8000/ui/interop/dashboard
- http://localhost:8000/ui/security/seeds
- http://localhost:8000/ui/security/safety

## Standalone Manual Pipeline (Legacy UI)

The repository also ships a **legacy standalone manual pipeline** page that mirrors the 10/06 experience. It remains fully
isolated from the Engine V2 surfaces and can be toggled on demand.

### Highlights

- Full-width cards for **Generate**, **De-identify**, **Validate**, **MLLP**, and more.
- Typed controls for **Trigger**, **Count**, **Seed**, and **Enrich** within Generate.
- Per-card “Next steps” trays that appear only after that module produces output.
- Rules dropdowns for De-ID and Validate sourced directly from the **Settings** templates in
  `configs/interop/deid_templates/` and `configs/interop/validate_templates/`.
- Live **De-ID processed-errors** and **Validate report** fragments rendered via HTMX.
- Smooth module handoff workflow (collapse current → open target → prefill message payloads).

### URL

- [`/ui/standalone/pipeline`](http://localhost:8000/ui/standalone/pipeline)

### Feature flag

The legacy UI is protected by an environment flag to keep V2-only deployments pristine:

```bash
# .env or shell
SILH_STANDALONE_ENABLE=1  # enable (default)
SILH_STANDALONE_ENABLE=0  # disable
```

When disabled:

- `/ui/standalone/*` routes are not registered.
- Legacy CSS/JS stays out of the bundle, preventing style bleed.

### Endpoint contracts

The standalone page relies on the existing interoperability endpoints. Ensure the following handlers are available:

| Purpose             | Method | Path                              | Notes                                                      |
|---------------------|--------|-----------------------------------|------------------------------------------------------------|
| Generate sample     | GET    | `/api/interop/sample`             | `version`, `trigger`, optional `seed=1`, `enrich=1`         |
| De-identify         | POST   | `/api/interop/deidentify`         | `message` or `file`, optional `deid_template`              |
| De-identify summary | POST   | `/api/interop/deidentify/summary` | **HTML** fragment; fields: `text`, `after_text`, `deid_template` |
| Validate (report)   | POST   | `/api/interop/validate/report`    | **HTML** fragment; accepts `message`, optional `val_template`    |
| MLLP send           | POST   | `/api/interop/mllp/send`          | `host`, `port`, `message`                                   |
| Pipeline run        | POST   | `/api/interop/pipeline/run`       | `text` (HL7) plus preset parameters                         |

The rules dropdowns use small helper routes that simply expose `<datalist>` options:

| Purpose                  | Method | Path                                      | Returns                  |
|--------------------------|--------|-------------------------------------------|--------------------------|
| De-ID templates datalist | GET    | `/ui/standalone/deid/templates`           | `<datalist>...</datalist>` |
| Validate templates list  | GET    | `/ui/standalone/validate/templates`       | `<datalist>...</datalist>` |

Templates live under:

```
configs/interop/deid_templates/*.json
configs/interop/validate_templates/*.json
```

### Dev notes

- Legacy CSS is scoped beneath `.legacy-interop-skin` in `static/legacy/**` and `static/standalone/**`.
- `static/standalone/pipeline.js` only targets standalone DOM IDs and trays.
- Tailwind’s safelist keeps legacy-only classes intact during production builds (see `tailwind.config.js`).

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

