# Silhouette Core Roadmap

This roadmap locks post-Phase-1 direction: agent-first, domain-agnostic, self-hosted, with a small distillation path.

---

## 0–2 Weeks: Harden the MVP (safe, testable, repeatable)

**Goals**
- Replace demo math tool with a **safe evaluator**.
- Add a tiny **eval runner** that exercises the *Agent* (not just the model).
- Create **run artifacts** (JSONL logs, eval report).
- Expand **persona deny_on** tests.
- Basic repo hygiene (pinned deps, make targets).

**Deliverables**
- Safe calculator tool (AST-based).
- `eval/eval.py` runner + CI gate on `eval/suites/basics.yaml`.
- `artifacts/session.log.jsonl` + `artifacts/eval_report.json` written by runs.
- 3–5 deny patterns in `docs/alignment_kernel/persona.dsl` + tests.
- Updated `requirements*.txt`, `make dev`, `make test`.

**Acceptance Criteria**
- Eval suite passes in CI.
- No use of `eval()` in tools.
- Logs written per session.
- Persona deny tests pass.

---

## Weeks 3–4: Data prep & first training dry-run (tiny)

**Goals**
- Seed a **small dataset** (10–50 samples) covering Q&A, tool calls, and denials.
- Execute **SFT** using existing `silhouette_core/training_loop.py`.
- Quick eval: stub vs. base vs. student.

**Deliverables**
- `training_data/core.jsonl` + `training_data/README.md` (data card).
- Run `python -m training.train_sft --cfg config/train.yaml` → `models/student-core/`.
- Re-run `eval/eval.py` with student wired into the Agent.

**Acceptance Criteria**
- SFT completes locally.
- Student improves over stub on simple Q&A and **preserves tool behavior**.
- `artifacts/eval_report.json` updated.

---

## Weeks 5–6: Distillation (teacher → student) & quantization preview

**Goals**
- Generate **teacher outputs** for a small set.
- Run **KD** via `silhouette_core/distiller.py` wrapper.
- Prototype **quantization**; measure CPU latency.

**Deliverables**
- `training_data/teacher_outputs.jsonl`.
- `python -m training.train_kd --cfg config/train.yaml` run completed.
- Export/quantize draft (INT8 or GGUF) + latency numbers recorded in README.

**Acceptance Criteria**
- KD student ≥ SFT student on core tasks.
- Quantized model runs on CPU with **< 3s** short-answer latency.

---

## Weeks 7–8: Focused “Profile” & self-check

**Goals**
- Introduce a **Profile** (allowed tools, tone, latency budget, deny rules).
- Extend `:selfcheck` to verify profile invariants.
- Expand eval suite.

**Deliverables**
- `profiles/core/policy.yaml`.
- `:selfcheck` checks: tools present, deny rules active, latency under budget.
- +10–20 eval cases (formatting, refusal quality, multi-turn).

**Acceptance Criteria**
- `:selfcheck` passes locally.
- Profile eval ≥ **90%** of targets.

---

## Operational add-ons (parallel, bite-sized)
- **CI/CD**: lint → tests → eval → package artifacts.
- **Observability**: counters for allow/deny, tool counts, avg latency.
- **Security**: prompt/response redaction; PII guard (regex stubs).
- **Model card**: `models/student-core/MODEL_CARD.md` (intended use, limits, evals).

