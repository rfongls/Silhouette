# Changelog

All notable changes to this project will be documented here.

## [Unreleased]
- PR-XX: **Plug-and-Play Dashboards**
  - Security & Interop dashboards now ship **KPI bars**, **Quick Start** actions, and **demo data**.
  - **OOB KPI refresh**: action responses inject small fragments so KPIs update instantly.
  - **Severity buckets** derived from CVSS when available.
  - Persist lightweight trend indices to `out/**/ui/index.json` for **History** sparklines.
  - **Example libraries**: HL7 samples (`.hl7` + drafter JSON), Interop & Security demo results, and a FHIR bundle.
  - **Smoke tests**: verify KPI summaries render and index files are written.
- PR-24: Packaging & CLI UX – pip package, unified `silhouette` CLI, distribution artifacts.
- PR-25: Edge targets – INT8/ONNX/GGUF exports and edge latency probe.
- PR-26: Release playbook & provenance artifacts – CI GitHub release workflow with scoreboard, gate summary, watermark.
- PR-27: License ops – customer license issuance tooling & watermark embedding.
- Docs normalization + parity fixes.

## Phase 10 – Release & Licensing (PR-26 → PR-27)
- Release playbook and artifact bundling.
- Customer license issuance with watermark embedding.

## Phase 9 – Packaging & Edge Deployment (PR-24 → PR-25)
- pip package and unified CLI.
- Edge quantization targets and latency probe JSON.

## Phase 8 – Continuous Improvement Flywheel (PR-22 → PR-23)
- Auto-promote runtime traces into curated buckets.
- Regression gates with latency budgets surfaced on scoreboard.

## Phase 7 – Cross-Language Runtime Expansion (PR-19 → PR-21)
- Cross-language runtime reframing.
- Web + Python runtime evals and linters (PR-20).
- C++/CMake runtime evals with optional clang-tidy (PR-21).

## Phase 6 – Compliance & Provenance (PR-15 → PR-18)
- Build runner prompt archival and FileFence adapter.
- Phase scoreboards, history, and trends.
- Security & compliance guardrails (redaction, PII, SPDX).
- Watermarks and customer license template.

## Phase 5 – Skills & Dataset Flywheel v1 (PR-12 → PR-14)
- Skill registry with versioned `skill@vN`.
- Scoreboard HTML artifact.
- Dataset synthesis from runtime passes.

## Phase 4 – Profiles & Evals (PR-10 → PR-11.2)
- Policy profiles and self-check.
- Developer eval suites and runtime compile/run evals.

## Phase 3 – Distillation & Quantization (PR-6 → PR-9)
- KD wrapper training student model.
- INT8 quantization stubs and latency probe.

## Phase 2 – Training Foundation (PR-4 → PR-5)
- Seed dataset and SFT wrapper.
- Dry-run training loop.

## Phase 1 – Core Agent Hardening (PR-1 → PR-3)
- Safe calculation tool with unit tests.
- Eval runner, session logging, deny rules.

## Early History
- CLI bootstrapping with dynamic modules and logs.
- Intent engine, tone parser, and memory system with FastAPI endpoints.
- Conversation graph engine with semantic recall.
- Offline-first recovery tools and performance profiling.
- Multi-agent interface and messaging with memory merge.
- Monitoring tools for drift, summaries, persona audits.
- Self-replication: profile export, distillation, packaging, quantization, deployment helpers.
