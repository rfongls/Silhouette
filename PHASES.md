## Phase 1 — Usable, Self-Hosted Agent
- Agent loop with:
  - Alignment DSL (deny_on + tone)
  - Explicit tool invocation via `use:<tool> ...`
  - Local model generation (`transformers`) or offline stub
- CLI wired to agent (not a chat wrapper)
- Minimal eval suite `eval/suites/basics.yaml`

## Phase 2 — Distillation (Reuse Existing Trainers)
- Adapters (`training/adapters/*`) & dataloader
- Thin wrappers that call:
  - `silhouette_core/training_loop.py` (SFT)
  - `silhouette_core/distiller.py` (KD)
- Quantization/export planning
- Eval harness + suites

## Phase 3 — Focused Agents
- Profiles, tool bundles, operational selfcheck, optional API
