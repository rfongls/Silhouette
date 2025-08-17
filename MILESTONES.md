# Milestones

## Phase 1 Hardening (0–2 weeks)
- [ ] Replace demo `calc` with safe evaluator + unit tests.
- [ ] Add `eval/eval.py`; gate CI on `eval/suites/basics.yaml`.
- [ ] Write `artifacts/session.log.jsonl` & `artifacts/eval_report.json` on runs.
- [ ] Add 3–5 `deny_on` patterns; tests for trigger & non-trigger.
- [ ] Pin `requirements*.txt`; add `make dev` / `make test`.

## Phase 2 Seed SFT (weeks 3–4)
- [ ] Create `training_data/core.jsonl` (10–50 samples) + data card.
- [ ] Run SFT via `training.train_sft` → `models/student-core/`.
- [ ] Agent uses student; eval passes & improves over stub.
- [ ] Store `artifacts/eval_report.json`.

## Phase 3 KD + Quant (weeks 5–6)
- [ ] Generate `training_data/teacher_outputs.jsonl`.
- [ ] Run KD via `training.train_kd`; compare vs SFT.
- [ ] Export/quantize draft (INT8/GGUF); record CPU latency (<3s short answer).

## Phase 4 Profile & Self-check (weeks 7–8)
- [ ] Add `profiles/core/policy.yaml` (tools, tone, latency budget, deny).
- [ ] Extend `:selfcheck` to validate profile invariants.
- [ ] Expand eval suite by 10–20 cases; achieve ≥90% target.

