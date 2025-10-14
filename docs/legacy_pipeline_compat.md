# Standalone Manual Pipeline (Classic QA Bench)

The classic Manual Pipeline (QA bench) now lives on its own dedicated page at `/ui/standalonepipeline`. It preserves the pre-V2 look and flow—Generate → De-identify → Validate → Send—without toggles or environment variables, while the modern `/ui/interop/pipeline` page stays unchanged for V2 work.

## Routing and adapter

* `api/ui_standalone.py` builds the context expected by the classic templates. It provides safe URL lookups, preset defaults, and template listings.
* The router is mounted from `server.py`, so navigating to `/ui/standalonepipeline` works without extra configuration.

## Templates and static assets

All standalone assets are namespaced so styles do not leak into other pages:

* Templates: `templates/ui/standalone/`
* Static assets: `static/standalone/`

## Manual verification checklist

1. Start the UI server (for example with `scripts/run_ui.bat`).
2. Navigate to **Interoperability → Manual Pipeline** and confirm it opens `/ui/standalonepipeline` with the classic layout.
3. Exercise the Generate, De-identify, Validate, and MLLP panels; each should populate its respective output area.
4. Run the full pipeline form and confirm validated HL7 output auto-fills and sends via the MLLP panel when enabled.
5. Visit `/ui/interop/pipeline` to confirm the V2 interface still loads normally.
