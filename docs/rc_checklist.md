# Release Candidate Checklist

## Scope Lock
### In (must ship)
- Repo map + HTML
- JS/TS parsing + unified graph
- Chunking + embeddings
- Retrieval planner + CLI analyses
- Propose-patch dry-run (outputs diff, impact, and PR body artifacts; allowed as
  dry-run but still filters protected paths)
- HL7 guardrails
- Offline check

### Out (defer)
See [parking_lot.md](parking_lot.md) for deferred follow-ons.

## Backlog Triage
### Blockers
- ✅ No SyntaxErrors, failing tests, or CLI crashes
- ✅ Propose_patch documented as dry-run with protected-path filtering
- ✅ Propose_patch emits diff, impact, and PR body artifacts

### Critical Quality
- ✅ Deterministic outputs (HTML/JSON ordering, diff ordering, newline normalization)
- ✅ record_run wraps multi-artifact commands
- ✅ README links and CLI help entries present

### Nice-to-haves
- ⚠️ Minor ruff nits outside `silhouette_core/**` and `tests/**` waived for RC

## RC Readiness
- ✅ Scope locked
- ✅ Backlog triaged
- ✅ Determinism checks pass
- ✅ Propose_patch artifacts captured
- ✅ Offline workflow validated
- ✅ Documentation finalized
