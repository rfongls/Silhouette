# Silhouette UI — Dashboard Progress Log

**Current Target:** Ship FastAPI + Jinja2 + HTMX UI with modular dashboards (Security, Interop, Admin), fully offline.

## Phase Status
- Phase 0 — Bootstrapping (App shell): ☐
- Phase 1 — Cybersecurity Dashboard (MVP): ☐
- Phase 2 — Interoperability Dashboard (HL7/FHIR): ☐
- Phase 3 — History Explorer: ☐
- Phase 4 — Seeds & Safety Editors: ☐
- Phase 5 — Theming & Template Integration: ☐
- Phase 6 — Advanced UX (Optional): ☐

## Phase 0 — Bootstrapping
**Planned:** App skeleton, static mount, base layout, run instructions.  
**Done:** _(codex: fill in)_  
**Notes:** _(codex: fill in)_

## Phase 1 — Cybersecurity Dashboard (MVP)
**Planned:**
- `/ui/security/dashboard` renders 4 cards
- `/security/{gate|recon|netforensics|ir}` JSON endpoints
- Results written to `out/security/ui/active/`
**Done:** _(codex: fill in)_  
**Notes:** _(codex: fill in)_

## Phase 2 — Interoperability Dashboard (HL7/FHIR)
**Planned:**
- `/ui/interop/dashboard` (HL7 draft/send, Translate, Validate)
- Implement function calls or CLI fallback
**Done:** _(codex: fill in)_  
**Notes:** _(codex: fill in)_

## Phase 3 — History Explorer
**Planned:** `/ui/security/history`, `/ui/interop/history` list `out/<toolpack>/*/active/*.json`  
**Done:** _(codex: fill in)_  
**Notes:** _(codex: fill in)_

## Phase 4 — Seeds & Safety Editors
**Planned:** `/ui/security/seeds`, `/ui/security/safety` edit seeds, scope, and env toggles  
**Done:** _(codex: fill in)_  
**Notes:** _(codex: fill in)_

## Phase 5 — Theming & Template Integration
**Planned:** Replace CSS/markup to match house theme  
**Done:** _(codex: fill in)_  
**Notes:** _(codex: fill in)_

## Phase 6 — Advanced UX (Optional)
**Planned:** Log streaming, bulk runs, summaries, concurrency tests  
**Done:** _(codex: fill in)_  
**Notes:** _(codex: fill in)_

## Commits / Milestones
- 2025-09-__ — Phase 0 app shell created
- 2025-09-__ — Phase 1 security dashboard MVP
- 2025-09-__ — Phase 2 interop dashboard MVP
- 2025-09-__ — Phase 3 history explorer
- 2025-09-__ — Phase 4 seeds & safety editors
- 2025-09-__ — Phase 5 theming applied
- 2025-09-__ — Phase 6 advanced UX

## Risks / Notes
- Offline-first: vendor all assets; prefer wheelhouse in CI and local setup.
- Safety: enforce gate preconditions visually; deny ambiguous configs.
- Windows: file upload paths and `out_dir/uploads` must be normalized.
- Interop CLI fallback: ensure subprocess calls never rely on external network.
