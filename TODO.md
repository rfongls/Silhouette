# TODO (Current Focus)
## MVP Hardening
- [ ] Safe calculator tool (AST parser) + tests (malformed, length, div-by-zero).
- [ ] `eval/eval.py` to run `eval/suites/basics.yaml`; exit non-zero on failure.
- [ ] JSONL interaction logging per turn (hash, len, allow/deny, tool, latency).
- [ ] Add 3–5 persona `deny_on` patterns + unit tests.
- [ ] Pin `requirements*.txt`; add `make dev` / `make test`.

## Data & Training
- [ ] `training_data/core.jsonl` + `training_data/README.md`.
- [ ] Run SFT and save to `models/student-core/`; wire student into Agent for eval.
- [ ] Save `artifacts/eval_report.json`.

## Distillation & Quantization
- [ ] Produce `training_data/teacher_outputs.jsonl`.
- [ ] Run KD and compare to SFT on basics suite.
- [ ] Prototype export/quantization; record CPU latency in README.

## Profiles & Self-check
- [ ] Create `profiles/core/policy.yaml`.
- [ ] Extend `:selfcheck` to assert profile constraints.
- [ ] Expand `eval/suites/*` (multi-turn, formatting, refusals).

## Ops
- [ ] CI workflow to run: ruff → tests → `eval/eval.py`.
- [ ] Add counters (allow/deny/tool/latency) to logs or metrics stub.
- [ ] Log redaction + simple PII regex guard.
- [ ] Draft `models/student-core/MODEL_CARD.md`.
