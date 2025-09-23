# Interop Settings UI

The settings workspace at `/ui/settings` lets analysts manage reusable
interoperability templates without touching the filesystem. Two template types
are supported:

* **De-identify templates** – HL7 segment/field selectors mapped to an action
  (`redact`, `mask`, `hash`, or `replace`) plus an optional parameter.
* **Validation templates** – Field requirements, optional regex patterns, and
  allowed value lists that power the validation step of the pipeline.

Each template lives as canonical JSON under
`configs/interop/deid_templates/` or `configs/interop/validate_templates/`.
Analysts can import/export CSV for spreadsheet workflows, but the JSON payloads
remain the source of truth.

## UI Overview

* **Settings index** – Lists existing templates and exposes quick-create
  actions. HTMX forms allow inline creation without a page reload.
* **Template editor** – A detail view for a specific template. New rules/checks
  are added one at a time, with the resulting table refreshed via HTMX swaps.
  Delete buttons remove individual entries instantly. CSV import updates the
  table without leaving the page, and JSON/CSV exports stream the current
  template definition.

## Runtime Integration

The Interop dashboard and pipeline screens surface dropdowns populated directly
from the JSON filenames in the configs directories. Selected templates are
threaded through to the runtime endpoints:

* The **De-identify** stage uses `apply_deid_with_template` to enforce the
  configured rules.
* The **Validate** stage feeds `validate_with_template`, surfacing issues in the
  UI and API responses.

If a requested template is missing or malformed, the API returns a 400-level
error with a descriptive message so the UI can surface the failure cleanly.
