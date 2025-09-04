# Silhouette UI — Dashboard TODO (Build Plan)

**Goal:** Deliver an offline-first, Windows-friendly **browser UI** that wraps multiple toolpacks:
- **Cybersecurity** (Gate, Recon, Netforensics, IR Playbook, Extensions)
- **Interoperability (HL7/FHIR)** (HL7 draft/send, HL7→FHIR translate, FHIR validate)
- (Optional later) Research toolkit (PDF→Index, Retrieve)
- **Admin** (Seeds, Safety toggles, History)

**Tech:** FastAPI + Jinja2 + HTMX (no frontend build), vendored `static/htmx.min.js`, offline wheelhouse, no database.

Legend: **Implement** • **Test** • **DoD** (Definition of Done)

---

## Phase 0 — Project Bootstrapping (App skeleton)

- **Implement**
  - Create `main.py` (FastAPI app, mount `/static`, register routers; returns a short `{"ok": true}` at `/`).
  - Create directories:
    ```
    api/                 templates/                 static/
    api/ui_security.py   templates/layout.html      static/htmx.min.js
    api/ui_interop.py    templates/security/...
    api/ui_admin.py      templates/interop/...
    ```
  - Vendor `static/htmx.min.js` (no CDN).  
  - Basic `templates/layout.html` skeleton with CSS link to `static/css/app.css` (create file).

- **Test**
  - `uvicorn main:app --host 127.0.0.1 --port 8000` starts locally.  
  - Navigating to `/` returns JSON.

- **DoD**
  - App runs offline.
  - No external HTTP requests by the UI shell.

---

## Phase 1 — Cybersecurity Dashboard (MVP)

**Routes & Endpoints**
- **UI**: `GET /ui/security/dashboard` → renders four cards
- **API**:
  - `POST /security/gate` → calls `skills.cyber_pentest_gate.v1.wrapper.tool`
  - `POST /security/recon` → calls `skills.cyber_recon_scan.v1.wrapper.tool`
  - `POST /security/netforensics` → calls `skills.cyber_netforensics.v1.wrapper.tool`
  - `POST /security/ir` → calls `skills.cyber_ir_playbook.v1.wrapper.tool`

**Forms (per card)**
- Gate:
  - Fields: `target` (text), `scope_file` (default `docs/cyber/scope_example.txt`), `auth_doc` (file), `out_dir` (default `out/security/ui`)
  - POST → inject JSON result into `<pre>` via HTMX
- Recon:
  - Fields: `target`, `scope_file`, `profile` (`safe`/`version`/`full`), `out_dir`
- Netforensics:
  - Fields: `pcap` (file upload), `out_dir`
- IR Playbook:
  - Fields: `incident` (`ransomware`/`credential`/`pii`), `out_dir`

- **Implement**
  - `api/security.py`: implement the four JSON endpoints (file saves to `out_dir/uploads`).
  - `templates/security/dashboard.html`: four cards with HTMX forms and `<pre id="*-result">`.

- **Test**
  - Each form submission returns `{"ok": true, "result": "<path>"}`.
  - Result file exists under `out/security/ui/active/`.
  - On Windows (CMD), uploads and writes succeed.

- **DoD**
  - All four flows run offline, mirror the wrapper behavior.
  - UI requires no external network.

---

## Phase 2 — Interoperability Dashboard (HL7/FHIR)

**Routes & Endpoints**
- **UI**: `GET /ui/interop/dashboard`
- **API**:
  - `POST /interop/hl7/draft-send` (exists)  
    - Inputs: `message_type`, `json_data` (textarea), `host`, `port`  
    - Calls: `skills.hl7_drafter.draft_message`, `skills.hl7_drafter.send_message`
  - `POST /interop/translate`  
    - Inputs: `hl7_file` (upload), `bundle` (`transaction|collection`), `validate` (bool), `out_dir` (default `out/interop/ui`)
    - Execute **one**:
      - Python function if available (e.g., `pipelines.hl7_to_fhir.translate`)
      - **OR** CLI fallback: `python -m silhouette_core.cli fhir translate --in <file> --bundle <x> --out <out_dir> [--validate]`
  - `POST /interop/validate`  
    - Inputs: `fhir_files[]` (multiple `.ndjson`)
    - Execute **one**:
      - Python validators if available  
      - **OR** CLI fallback: `python -m silhouette_core.cli fhir validate --in-dir <dir>`

- **Implement**
  - `api/interop.py`: keep draft-send; add translate/validate (prefer function; fallback to subprocess).
  - `templates/interop/dashboard.html`: cards for Draft/Send, Translate, Validate (HTMX forms → `<pre>`).

- **Test**
  - Draft/Send returns `{"message": "...", "ack": "..."}` with a running MLLP echo server (or a stub).
  - Translate returns `rc`, `stdout`, `stderr`, and `out` folder path.
  - Validate returns summary (rc + stdout stderr) or function results.

- **DoD**
  - Interop dashboard runs offline (CLI fallback uses only local exec).
  - Uploads and outputs are organized under `out/interop/ui/...`.

---

## Phase 3 — History Explorer (Security & Interop)

- **Implement**
  - `GET /ui/security/history`: list `out/security/*/active/*.json` sorted desc; link to file viewer/download.
  - `GET /ui/interop/history`: list `out/interop/*/active/*.json` similarly.
  - Optional: add simple prettifiers for recon services, netforensics alerts; raw JSON always available.

- **Test**
  - With several runs present, UI lists latest runs and opens artifacts.

- **DoD**
  - Runs list efficiently; opening large JSONs doesn’t crash the page.

---

## Phase 4 — Seeds & Safety Editors

- **Implement**
  - Seeds UI: `GET /ui/security/seeds`  
    - Textareas to edit:
      - `data/security/seeds/cve/cve_seed.json`
      - `data/security/seeds/kev/kev_seed.json`
      - `docs/cyber/scope_example.txt`
    - `POST /admin/seeds/save` → backup old → validate JSON (for CVE/KEV) → write new; show parse errors inline.
  - Safety UI: `GET /ui/security/safety`  
    - Inputs/map to:
      - `CYBER_KILL_SWITCH`, `CYBER_DENY_LIST`, `CYBER_PENTEST_WINDOW`, `CYBER_THROTTLE_SECONDS`, `CYBER_ALLOWLIST`, `CYBER_DNS_DIR`, `CYBER_HTTP_DIR`
    - `POST /admin/safety/save` → update `.env` or `config/security.env`

- **Test**
  - Invalid JSON shows error; valid saves persist.
  - Safety toggles persist and reflect back in UI.

- **DoD**
  - Editors work offline, with backups and clear feedback.

---

## Phase 5 — Theming & Template Integration

- **Implement**
  - Replace `static/css/app.css` with your team’s base theme (supply your sample).
  - Adjust `templates/layout.html` and card markup to match theme components (buttons, inputs, grid).

- **Test**
  - Visual consistency across Security/Interop/Admin pages.
  - No CDN or external fonts; fully offline.

- **DoD**
  - All pages restyled to your standard theme.

---

## Phase 6 — Advanced UX (Optional)

- **Implement**
  - Log streaming (WebSockets/SSE) for long operations (e.g., recon, translate).
  - Bulk runs (multi-target) with in-process queue.
  - Prettified summaries (tables/badges) and JSON toggles.
  - Artifact upload in CI (already added in workflows).

- **Test**
  - Concurrency: multiple submissions don’t block or drop responses.
  - Streaming updates render smoothly with HTMX or JS fallback.

- **DoD**
  - Non-blocking UX confirmed; summaries readable; raw JSON always accessible.

---

## Directory & File Checklist (to scaffold)

- **Core**
  - [ ] `main.py` (register routers, mount static)
  - [ ] `api/security.py` (4 JSON endpoints)
  - [ ] `api/ui_security.py` (dashboard, history, seeds, safety views)
  - [ ] `api/interop.py` (draft-send + translate/validate endpoints)
  - [ ] `api/ui_interop.py` (dashboard, history views)
  - [ ] `api/ui_admin.py` (global safety editor; optional)
  - [ ] `templates/layout.html`
  - [ ] `templates/security/dashboard.html`
  - [ ] `templates/security/history.html`
  - [ ] `templates/security/seeds.html`
  - [ ] `templates/security/safety.html`
  - [ ] `templates/interop/dashboard.html`
  - [ ] `templates/interop/history.html`
  - [ ] `static/htmx.min.js` (vendored)
  - [ ] `static/css/app.css` (your theme)
- **Optional**
  - [ ] `templates/partials/*.html` (result blocks, tables, badges)
  - [ ] `scripts/start_ui.bat` (seed/install/start uvicorn on Windows)

---

## Offline & CI Notes

- Prefer offline wheelhouse install (`offline/wheels` + `offline/requirements.lock`) in CI.  
- Upload `out/security/**` and `out/interop/**` as CI artifacts.  
- All UI pages must load without external network calls.

---

## Acceptance Test Snippets

- Start:
```

uvicorn main\:app --host 127.0.0.1 --port 8000

```
- Cyber Gate: submit target/auth → `pentest_gate.json` & `pentest_gate_audit.json`
- Recon version: verify CVE-0001 flagged `kev: true` in HTTP service
- Netforensics: empty pcap → JSON with `packets`, `flows`, `index`, `alerts`
- IR Playbook: `incident="ransomware"` → populated playbook sections
- HL7 Draft/Send: message + ACK shown
- Translate/Validate: CLI fallback returns `rc/stdout/stderr/out` and artifacts
```

---
