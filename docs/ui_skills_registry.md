# Skills Registry & Dashboard Architecture

Silhouette Core separates **Reports** (summaries/KPIs) from **Skills** (dashboards with tools).

---

## Overview

- **Reports Home (`/ui/home`)**
  - Shows high-level KPIs and recent activity across all enabled skills.
  - Each skill contributes a KPI card by exposing a `summary_url`.

- **Skills Index (`/ui/skills`)**
  - Lists all available skill dashboards (Interop, Security, etc.).
  - Links into each dashboard for detailed tools.

- **Skill Dashboards (`/ui/<skill>/dashboard`)**
  - Provide feature panels (Generate, Scan, IR Playbook, etc.).
  - Panels use **HTML-friendly endpoints** under `/ui/<skill>/*`.
  - “Reports view” toggle can hide feature panels and show KPI-only.

---

## Registry

Skills are defined in `config/skills.yaml`:

```yaml
skills:
  - id: interop
    name: Interoperability
    desc: Generate/de-ID/validate HL7, translate to FHIR, and transport via MLLP.
    dashboard: /ui/interop/dashboard
    summary_url: /interop/summary
    enabled: true

  - id: security
    name: Security
    desc: Run security tools, capture evidence, and review findings.
    dashboard: /ui/security/dashboard
    summary_url: /security/summary
    enabled: true
```

### Fields

- **id**: short identifier (used in IDs/logging)
- **name**: display name for UI tiles/cards
- **desc**: short description text
- **dashboard**: route to the skill dashboard
- **summary_url**: endpoint that returns a small **HTML** KPI block for Reports home
- **enabled**: toggle visibility (true/false)

---

## Adding a New Skill

1) **Registry** — Add an entry to `config/skills.yaml`.

2) **Backend** — Create `api/<skill>.py` with:
   - `<skill>/summary` → **HTML** KPI block
   - `/ui/<skill>/*` → **HTML-friendly** endpoints for each tool panel

3) **Templates** — Create:
   - `templates/ui/<skill>/dashboard.html` (top-level)
   - partials like `templates/ui/<skill>/_<panel>_panel.html` (feature cards)

4) **Restart**
   ```bash
   uvicorn server:app --reload
   ```

5) **Verify**
   - Appears on `/ui/home` (Reports) with a KPI card
   - Appears on `/ui/skills` with a tile
   - Dashboard loads under `/ui/<skill>/dashboard`

---

## Design & UX Notes

- **HTML endpoints, not JSON.**  
  All panel actions (`/ui/<skill>/*`) should return **HTML fragments** so HTMX swaps render cleanly (no raw JSON in cards).

- **Feature toggles**  
  Dashboards can mark feature cards with `data-feature="name"` and use the shared JS to hide/show or switch to “Reports view”.

- **Shared assets**  
  - Base spacing/layout: `/static/css/dashboard.css`
  - Interop add-ons & utility styles: `/static/css/interop_extras.css`
  - Minimal nav highlighting: `/static/js/nav.js`
  - Interop UI helpers (toggles, datalists): `/static/js/interop_ui.js`

---

## Interop-Specific Notes

- **Trigger descriptions** live in `templates/hl7/trigger-events-v2.csv`.  
  The Interop dashboard loads descriptions from the CSV (mtime-cached) and shows `TRIGGER — Definition` in lists/typeahead.

- **Folder-backed trigger selection**  
  `/ui/interop/triggers` returns `<option>`s generated from `templates/hl7/<version>/*.hl7`;  
  `/api/interop/triggers` returns JSON for `<datalist>` typeahead.

---

## File Map (key UI pieces)

```
config/
  skills.yaml                 # registry (optional; defaults baked-in if missing)

api/
  ui.py                       # loads registry, routes /ui/home & /ui/skills
  interop.py                  # Interop UI/HTML endpoints + samples/maps
  security.py                 # Security UI/HTML endpoints + summary

templates/
  layout.html                 # global layout; nav for Reports/Skills
  ui/
    home_reports.html         # Reports Home (renders all enabled skills)
    skills_index.html         # Skills Index (tiles to dashboards)
    interop/
      dashboard.html
      _sample_list.html
      _deid_panel.html
      _validate_panel.html
      _mllp_panel.html
      ... other panels
    security/
      dashboard.html
      _scan_panel.html
      _recon_panel.html
      _pentest_panel.html
      _ir_panel.html

static/
  css/dashboard.css           # spacing/theme hooks for dashboards
  css/interop_extras.css      # card/gap utilities
  js/nav.js                   # nav highlighting
  js/interop_ui.js            # feature toggles & interop typeahead datalists
```

---

## Why HTML Fragments?

- With HTMX, returning HTML makes panels **copy-pasteable** and reliable in dev/prod.
- You avoid double-rendering JSON → HTML in the browser.
- KPIs and error messages remain readable, not raw JSON.

---

## Future Extensions

- Add `sections:` to registry to surface subpages (e.g., tabs or side-nav) inside a skill.
- Add `roles:` to hide skills or panels based on user permissions.
- Add `summary_interval:` to control refresh for each skill’s KPI card.
- Make the **Recent Activity** feed configurable per skill (e.g., `activity_url`).

---

## Troubleshooting

- **No skills showing:**  
  Check `config/skills.yaml` — do entries have `enabled: true`?

- **No KPI card on Reports Home:**  
  Make sure the registry entry defines `summary_url` and the endpoint returns small **HTML**.

- **Interop triggers empty:**  
  Ensure `templates/hl7/<version>/*.hl7` files exist and the CSV (optional) matches the headers (`Trigger`, `Definition`).
