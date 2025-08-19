# Phases

**Status: Phase 10 complete**

## Phase 1 — Core Agent Hardening (PR-1 → PR-3)
- Safe calc, eval runner, deny rules, logging.
- Goal: Make the minimal agent safe and testable.

## Phase 2 — Training Foundation (PR-4 → PR-5)
- Seed dataset, SFT wrapper, dry-run training.
- Goal: Establish initial training loop.

## Phase 3 — Distillation & Quantization (PR-6 → PR-9)
- Teacher outputs, KD, quantization, latency probe.
- Goal: Smaller student model runs offline, faster.

## Phase 4 — Policy & Evals (PR-10 → PR-11.2)
- Profiles + self-check.
- Developer eval suites, runtime compile cases.
- Goal: Build evaluation harness across stacks.

## Phase 5 — Skills & Dataset Flywheel v1 (PR-12 → PR-14)
- Skill registry, versioned skills, scoreboard.
- Runtime traces → KD dataset synthesis.
- Goal: Let the agent ingest skills and learn from runtime wins.

## Phase 6 — Compliance & Provenance (PR-15 → PR-18)
- Build runner prompt archival + file-fence adapter.
- Phase scoreboards + history + trends.
- Security & compliance guardrails (redaction, PII, SPDX).
- Watermarks + customer license template.
- Goal: Ensure every artifact has provenance & compliance baked in.

## Phase 7 — Cross-Language Runtime Expansion (PR-19 → PR-21)
- Reframe as cross-language capability (not an app).
- Add Web, Python, C++/CMake runtimes + linters.
- PR-20: Web + Python runtime evals and linter integration
- PR-21: C++ / CMake runtime evals + optional clang-tidy lint
- Goal: Full multi-language coverage.

## Phase 8 — Continuous Improvement Flywheel (PR-22 → PR-23)
- PR-22: Auto-promote runtime traces into curated lane buckets.
- PR-23: Regression gates & latency targets per lane; CI fails on regressions; gates surfaced on scoreboard/history.
- Goal: Make CI a continuous learning + regression safety net.

## Phase 9 — Packaging & Deployment (PR-24 → PR-25)
- PR-24: pip package, unified CLI, profiles, wheels include eval/profiles/security/templates, CI artifacts on release.
- PR-25: Edge/on-device targets (GGUF, ONNX INT8); latency probe edge panel.
- Goal: Make Silhouette Core portable, installable, edge-ready.

## Phase 10 — Release & Licensing (PR-26 → PR-27)
- PR-26: Release playbook (RELEASE.md), CI GitHub release workflow, attach provenance artifacts.
- PR-27: Customer license issuance tooling, watermark embedding.
- Goal: Deliver Silhouette Core as a governed, licensable product.

## PR Index

| PR   | Title                                              | Status  | Purpose                                        |
| ---- | -------------------------------------------------- | ------- | ---------------------------------------------- |
| 1–3  | Agent Hardening                                    | ✅ Done | Safe calc, eval runner, deny patterns, logging |
| 4–5  | Data Prep + SFT                                    | ✅ Done | Seed dataset, dry-run training                 |
| 6–8  | KD Pipeline                                        | ✅ Done | Teacher outputs, KD run, eval reporting        |
| 9    | Quantization + Latency                             | ✅ Done | INT8 + latency probe                           |
| 10   | Profile + Self-check                               | ✅ Done | Policy, deny rules, latency gates              |
| 11   | Eval Suites                                        | ✅ Done | Basic developer evals                          |
| 11.2 | Runtime Compile/Run Evals                          | ✅ Done | FastAPI, ML, multi-file                        |
| 12   | Skill Registry + RAG-to-Skill                      | ✅ Done | Dynamic skill ingestion                        |
| 13   | Versioned Skills + Scoreboard                      | ✅ Done | Skill@vN, scoreboard HTML                      |
| 14   | Dataset Synthesis                                  | ✅ Done | Runtime → KD traces                            |
| 15   | Build Runner Archival + File-Fence Adapter         | ✅ Done | Prompts, zips, training adapter                |
| 15.2 | Phase Scoreboards                                  | ✅ Done | Phase snapshots linked                         |
| 16   | Scoreboard History                                 | ✅ Done | history.html                                   |
| 16.2 | Per-phase Summaries + Trends                       | ✅ Done | ▲/▼ badges                                     |
| 17   | Security & Compliance v1                           | ✅ Done | Redaction, PII, secrets, deny rules            |
| 18   | Containerized Runtime + Compliance v2 + Watermarks | ✅ Done | Java/.NET/Android builds, SPDX, watermarking   |
| 19   | Cross-Language Runtime Reframe                     | ✅ Done | Docs/CI clarity, Vision anchored               |
| 20   | Web + Python Runtimes + Linters                    | ✅ Done | Expand eval coverage                           |
| 21   | C++/CMake Runtimes                                 | ✅ Done | Add systems-level stack                        |
| 22   | Data Flywheel v2                                   | ✅ Done | Curated trace promotion                        |
| 23   | Regression Gates & Latency Targets                 | ✅ Done | CI thresholds per lane                         |
| 24   | Packaging & CLI UX                                 | ✅ Done | pip package, CLI polish                        |
| 25   | Edge Targets                                       | ✅ Done | GGUF/ONNX quantization                         |
| 26   | Release Playbook & Artifacts                       | ✅ Done | RELEASE.md, artifact bundle                    |
| 27   | License Ops                                        | ✅ Done | Customer license issuance & watermark embedding |

## Phase 10 Complete

Silhouette Core has completed Phase 10. The roadmap items through PR-27 are delivered, and the project is ready for governed release and licensing.

