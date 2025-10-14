# Legacy Manual Pipeline Compatibility Skin

This project includes a compatibility "legacy skin" for the Manual Pipeline (QA bench) so teams that rely on the original interface can keep their workflows while Engine V2 remains enabled.

## Switching between skins

* The `/ui/interop/pipeline` route defaults to the legacy skin.
* Append `?skin=v2` to the URL to reach the new V2 interface without changing defaults.
* Set the `SIL_INTEROP_LEGACY` environment variable to `0` to make the V2 interface the default (set it to `1` to keep the legacy skin as default).

## Legacy adapter

The adapter defined in `api/ui_legacy_pipeline.py` builds the context expected by the legacy templates. It provides:

* String URLs resolved through `url_for` with safe fallbacks.
* Preset connection values and defaults for MLLP and FHIR endpoints.
* Template listings for de-identification and validation dropdowns.

## Legacy assets and templates

Legacy-specific templates and static assets live under:

* `templates/ui/interop/legacy/`
* `static/legacy/interop/`

The CSS scopes styles under the `.interop-legacy` class so that the V2 interface remains unaffected.

## Registration

The FastAPI router from `api/ui_legacy_pipeline.py` is mounted in `server.py`, ensuring that the legacy skin remains available when requested.

## Manual verification checklist

1. Start the UI server (for example with `scripts/run_ui.bat`).
2. Navigate to **Interoperability → Manual Pipeline** and confirm the legacy layout is shown.
3. Run the Generate, De-identify, Validate, and Send panels in sequence; each panel should populate its corresponding output area.
4. Trigger the compat page with `/ui/interop/pipeline?skin=v2` to confirm the new interface still works.
5. Visit Engine pages (e.g., `/ui/engine`) to ensure they are unaffected.
