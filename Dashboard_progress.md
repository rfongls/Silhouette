# Silhouette UI — Dashboard Progress Log

**Current Target:** Ship FastAPI + Jinja2 + HTMX UI with modular dashboards (Security, Interop, Admin), fully offline.

## Phase Status
- Phase 0 — Bootstrapping (App shell): ☑
- Phase 1 — Cybersecurity Dashboard (MVP): ☑ ([/ui/security/dashboard](/ui/security/dashboard))
- Phase 2 — Interoperability Dashboard (HL7/FHIR): ☑ ([/ui/interop/dashboard](/ui/interop/dashboard))
- Phase 3 — History Explorer: ☑
- Phase 4 — Seeds & Safety Editors: ☑
- Phase 5 — Theming & Template Integration: ☑
- Phase 6 — Advanced UX (Optional): ☑

## Phase 0 — Bootstrapping
**Planned:** App skeleton, static mount, base layout, run instructions.  
**Done:** FastAPI app with static files and base layout template.  
**Notes:** Runs offline; root endpoint returns `{ "ok": true }`.

## Phase 1 — Cybersecurity Dashboard (MVP)
**Planned:**
- `/ui/security/dashboard` renders 4 cards
- `/security/{gate|recon|netforensics|ir}` JSON endpoints
- Results written to `out/security/ui/active/`
**Done:** Dashboard and endpoints implemented with HTMX forms and file upload handling.  
**Notes:** Writes artifacts under `out/security/ui/`.

## Phase 2 — Interoperability Dashboard (HL7/FHIR)
**Planned:**
- `/ui/interop/dashboard` (HL7 draft/send, Translate, Validate)
- Implement function calls or CLI fallback
**Done:** Added draft-send, translate, and validate endpoints with CLI fallback and HTMX UI.  
**Notes:** Outputs stored under `out/interop/ui/`.

## Phase 3 — History Explorer
**Planned:** `/ui/security/history`, `/ui/interop/history` list `out/<toolpack>/*/active/*.json`  
**Done:** History views list JSON artifacts with links for download.  
**Notes:** Simple listing; no prettifiers yet.

## Phase 4 — Seeds & Safety Editors
**Planned:** `/ui/security/seeds`, `/ui/security/safety` edit seeds, scope, and env toggles
**Done:** Seeds and safety editors added with backup + validation save endpoints.
**Notes:** Writes to `data/security/seeds/...` and `config/security.env`.

## Phase 5 — Theming & Template Integration
**Planned:** Replace CSS/markup to match house theme
**Done:** Base theme applied across layout, dashboards, and history pages.
**Notes:** Uses grid cards and offline CSS.

## Phase 6 — Advanced UX (Optional)
**Planned:** Log streaming, bulk runs, summaries, concurrency tests
**Done:** Added SSE endpoint for streaming recon results, bulk recon streaming, and HTML summaries for security and interop tools with inline JSON previews, vendored full HTMX, a concurrency smoke test, and non-blocking thread offloads for recon scans.
**Notes:** Streaming sequence verified for multi-target recon; history viewers now restrict paths under `out/`; added one-click launch scripts for Windows and macOS.

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
