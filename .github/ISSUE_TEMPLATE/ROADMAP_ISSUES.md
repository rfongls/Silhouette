# Roadmap Checklist (copy sub-items into separate issues if desired)

## MVP Hardening (0–2w)
- [ ] Safe `calc` tool (AST) + tests (malformed/length/div-by-zero)
- [ ] `eval/eval.py` runs `eval/suites/basics.yaml` and gates CI
- [ ] Write `artifacts/session.log.jsonl` and `artifacts/eval_report.json`
- [ ] Add 3–5 `deny_on` patterns + unit tests
- [ ] Pin requirements; add `make dev` / `make test`

## Data & Training (w3–4)
- [ ] `training_data/core.jsonl` + data card
- [ ] Run SFT; save to `models/student-core/`
- [ ] Wire student into Agent; re-run eval; store `artifacts/eval_report.json`

## KD & Quantization (w5–6)
- [ ] Generate `training_data/teacher_outputs.jsonl`
- [ ] Run KD; compare vs SFT on basics suite
- [ ] Export/quantize draft; record CPU latency in README

## Profile & Self-check (w7–8)
- [ ] `profiles/core/policy.yaml`
- [ ] Extend `:selfcheck` for profile invariants
- [ ] Expand eval suite (+10–20 cases; formatting/refusals/multi-turn; ≥90%)

