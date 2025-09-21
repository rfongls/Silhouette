# Documentation Index

## Getting Started
- [INSTALL_QUICKSTART](./INSTALL_QUICKSTART.md)
- **HL7 QA Validator** — run commands & options: [skills/hl7/](skills/hl7/)
- **FHIR Translator** — run commands & options: [skills/fhir/](skills/fhir/)
- Unified workflows: [skills/workflows/hl7_fhir_workflows.md](skills/workflows/hl7_fhir_workflows.md)
- Unified CLI (silhouette): [CLI.md](./CLI.md)
- API surface: [API.md](./API.md)
- Interoperability quickstart: [interoperability/quickstart.md](./interoperability/quickstart.md)

## Core Capabilities
- Agent loop and tool invocation: [Agents.md](./Agents.md)
- Offline mode (safe-mode, throttling): [Offline_Mode.md](./Offline_Mode.md)
- Knowledge Distillation: [Knowledge_Distillation.md](./Knowledge_Distillation.md)
- Quantization: [Quantization.md](./Quantization.md)
- Build deployable clone: [Package_Clone.md](./Package_Clone.md)

## Skills, Profiles, Security
- Skills registry & usage: [Skills.md](./Skills.md)
- Policy profiles (YAML): [Profiles.md](./Profiles.md)
- Security (license scanner, redaction, watermark): [Security.md](./Security.md)

## Reference
- Phases overview: [PHASES.md](../PHASES.md)
- Knowledge store hierarchy: [knowledge_store/hierarchy.md](./knowledge_store/hierarchy.md)
- Alignment kernel handoff: [alignment_kernel/](./alignment_kernel/)
- Map index: [reference/maps.md](reference/maps.md)
- Config reference: [reference/configs.md](reference/configs.md)

## Evaluation, Training, Config & Artifacts
- Evaluations & gates: [Eval.md](./Eval.md)
- Training (SFT/KD adapters): [Training.md](./Training.md)
- Config (gates, lanes, train): [Config.md](./Config.md)
- Artifacts (scoreboards, logs, traces): [Artifacts.md](./Artifacts.md)

## Project Ops
- Release playbook: ../RELEASE.md
- Changelog: ../CHANGELOG.md
- Compliance policy: ../COMPLIANCE.md
- Customer license template: ../CUSTOMER_LICENSE_TEMPLATE.md

# Silhouette — Logging, Reporting & Interop Pipelines

This pack documents how Silhouette logs and reports HL7 ↔ FHIR pipeline activity using **SQLite** (WAL), with a thin audit API and reporting endpoints.

**What’s included**
- Data model and schema (message versions, runs/tasks, MLLP sends, errors)
- Audit API (write + read)
- Validate reporting + MLLP ACKs search
- Pipeline run semantics & universal panel navigation
- Operational runbooks (retention, requeue)
- Security & privacy guardrails

The UI patterns align with our **Skills Dashboard** and **Interoperability Dashboard** prototypes, so wording and states match the product. 
