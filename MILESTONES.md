# Milestones

## PR-1 Safe math tool
- **Scope**: replace demo `eval` with AST-based `safe_calc` and unit tests.
- **Acceptance**: `pytest -q`, `python -m cli.main` → `use:calc 3*7` → `21`.

## PR-2 Eval runner and CI gate
- **Scope**: add `eval/eval.py`, baseline `basics.yaml`, and CI workflow.
- **Acceptance**: `python -m eval.eval --suite eval/suites/basics.yaml` passes.

## PR-3 Session logging & deny tests
- **Scope**: per-turn JSONL logs, expanded `deny_on` patterns, alignment tests, Makefile targets.
- **Acceptance**: `python -m cli.main`, `pytest -q`, `ruff check .`.

## PR-4 Seed dataset & data card
- **Scope**: add `training_data/core.jsonl` and `README` with schema and license.
- **Acceptance**: `python scripts/validate_jsonl.py training_data/core.jsonl`.

## PR-5 SFT plumbing run
- **Scope**: wire seed dataset into `training.train_sft` and produce `models/student-core/`.
- **Acceptance**: `python -m training.train_sft --cfg config/train.yaml`.

## PR-6 Agent uses student + eval report
- **Scope**: generator prefers `STUDENT_MODEL`; add `scripts/eval_report.py`.
- **Acceptance**: `STUDENT_MODEL=models/student-core python scripts/eval_report.py`.

## PR-7 Teacher outputs for KD
- **Scope**: add `training_data/teacher_outputs.jsonl` and generator helper.
- **Acceptance**: `python scripts/validate_teacher_jsonl.py training_data/teacher_outputs.jsonl`.

## PR-8 KD wrapper run
- **Scope**: reuse distiller to train KD model at `models/student-core-kd/`.
- **Acceptance**: `python -m training.train_kd --cfg config/train.yaml` and basics eval pass.

## PR-9 Quantization draft & latency probe
- **Scope**: `scripts/quantize.py` with INT8 stub, `scripts/latency_probe.py`.
- **Acceptance**: `python scripts/quantize.py --method int8 --src models/student-core-kd --out models/student-core-int8` and `python scripts/latency_probe.py`.

## PR-10 Profile + selfcheck
- **Scope**: `profiles/core/policy.yaml` and `scripts/selfcheck.py` verifying tools, deny, latency.
- **Acceptance**: `python scripts/selfcheck.py --policy profiles/core/policy.yaml`.

## PR-11 Advanced dev eval suites
- **Scope**: add regex-aware runner and language-specific suites (Android, Python, HTML/CSS, Java, C#).
- **Acceptance**: `python -m eval.eval --suite eval/suites/dev_python_advanced.yaml` (skips when offline).

## PR-11.2 Runtime dev evals
- **Scope**: runtime build runner and FastAPI/ML runtime suites.
- **Acceptance**: `python -m eval.build_runner --suite eval/suites/dev_python_fastapi_runtime.yaml --require_runtime_env` (skips offline).

## PR-12 RAG-to-Skill pipeline
- **Scope**: dynamic skill loading, skill registry, selfcheck skill verification, runtime skill suite.
- **Acceptance**: `python scripts/selfcheck.py --policy profiles/core/policy.yaml` includes skills ok.

## PR-13 Skill scoreboard + versioning
- **Scope**: versioned skills, promotion tool, HTML scoreboard artifact.
- **Acceptance**: `python scripts/scoreboard.py` and artifact upload in CI.

## PR-14 Dataset synthesis from runtime passes
- **Scope**: `scripts/synthesize_traces.py` + validator, make target, CI step.
- **Acceptance**: `python scripts/synthesize_traces.py` then `python scripts/validate_traces.py artifacts/traces/runtime_kd.jsonl`.

## PR-15 Build runner archival & file-fence adapter
- **Scope**: store prompts and zipped workdirs in runtime reports, add `FileFenceAdapter`, update docs.
- **Acceptance**: `python -m eval.build_runner --suite eval/suites/dev_python_fastapi_runtime.yaml --require_runtime_env` (produces prompt + zip), training via file-fence adapter in `config/train.yaml`.

## PR-18 Containerized runtime builds + compliance guardrails
- **Scope**: Docker-based runtime evals for Java/Maven, .NET/dotnet CLI, and Android/Gradle; SPDX license checks with whitelist and tunable thresholds; watermarking of model artifacts; customer license template.
- **Acceptance**: `ENABLE_RUNTIME_EVAL=1 python -m eval.build_runner --suite eval/suites/dev_java_runtime.yaml` and `python -m security.scanner --path . --license_whitelist MIT,Apache-2.0,BSD-2-Clause,BSD-3-Clause --license_denylist GPL-3.0,AGPL-3.0,MPL-2.0 --max_high 0 --max_medium 10 --max_low 999`.

## PR-19 — Cross-Language Containerized Runtime Evals (Java/.NET/Android) + Cache + Extended Evals + Phase-6 Scoreboards
- **Scope:** Agent-level capability to compile/test across stacks in Docker (Java/.NET/Android), with cache mounts and extended cases; phase-6 scoreboard snapshot.
- **Acceptance:** Cross-language suites pass; caches effective; scoreboard updated; docs emphasize "general agent" (not platform-specific).
