# Phases

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
- PR-23: Regression gates + latency targets per lane.
- Goal: Make CI a continuous learning + regression safety net.

## Phase 9 — Packaging & Deployment (PR-24 → PR-25)
- pip package + CLI UX.
- Edge/on-device quantization targets.
- Goal: Make Silhouette Core portable, installable, edge-ready.

## Phase 10 — Release & Licensing (PR-26 → PR-27)
- Release playbook, artifacts, scoreboard bundle.
- Customer license issuance tooling, watermark embedding.
- Goal: Deliver Silhouette Core as a governed, licensable product.

