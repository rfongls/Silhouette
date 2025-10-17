# Standalone Pipeline (Isolated Module)

This module restores the legacy standalone pipeline behavior (Generate → De-identify → Validate) without touching V2 code paths.

## URLs
- UI: `/standalone/`
- API: `/standalone/api/*`

## Template Resolution
The router prefers any existing repo templates/styles first, then falls back:
1. `templates/standalone/**` (your current standalone templates, if present)
2. `templates/standalone/legacy/**` (vendored legacy panel templates)

Optionally set `STANDALONE_TEMPLATE_ROOT=/absolute/or/relative/path` to override for experiments.

## Config Templates
- De-identification: `configs/standalone/deid_templates/*.json`
- Validation: `configs/standalone/validate_templates/*.json`

Defaults are created if directories are empty (a `default.json` is bootstrapped).

## Dev Notes
- The code imports *stable* non-V2 functions via `api/standalone/adapters.py`. If function locations change in your tree, update the adapters (kept isolated from V2).
- The CSS in `static/standalone/legacy.css` is loaded only for the `/standalone` page.
- If you already have `templates/standalone/index.html`, it will be used instead of `index_compat.html`.

## Smoke Test
1. Start the app and open `/standalone/`.
2. **Generate**: Submit → text appears in `#gen-output`, and the next panels un-collapse.
3. **De-identify**: Runs against selected template; plaintext output shown.
4. **Validate**: Renders an HTML report fragment using the legacy `_validate_report.html`.
