# Phases

## Phase 1 — Agent MVP Hardening
PR-1 to PR-3
- Replaced unsafe eval with safe math parser.
- Added eval runner + deny tests.
- Logging and requirements pinned.

## Phase 2 — Data Prep + SFT
PR-4 to PR-5
- Seed dataset creation.
- Dry-run SFT wrapper.
- Offline tokenizer fallback.
- [Scoreboard](artifacts/scoreboard/phase-2.html)


## Phase 3 — KD + Quantization
PR-6 to PR-9
- Teacher outputs and KD wrapper.
- Student eval reporting.
- Quantization utility and latency probes.
- [Scoreboard](artifacts/scoreboard/phase-3.html)


## Phase 4 — Profiles + Dev Evals + Skills
PR-10 to PR-14
- Profiles and self-check.
- Developer eval suites and runtime builds.
- Dynamic skills, registry ingestion, versioning, and dataset synthesis.
- [Scoreboard](artifacts/scoreboard/phase-4.html)


## Phase 5 — Runtime Archival + File-Fence Training
PR-15
- Build runner archives prompts and zipped workdirs.
- File-fence adapter enables multi-file SFT.
- Documentation synced with milestones.
- [Scoreboard](artifacts/scoreboard/phase-5.html)

