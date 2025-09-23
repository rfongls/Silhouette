# Interop Settings UI

The settings dashboard available at `/ui/settings` provides authoring tools for
two reusable interoperability templates:

* **De-identify templates** – HL7 segment/field selectors with an action of
  `redact`, `mask`, `hash`, or `replace`.  These drive runtime scrubbing within
  the de-identification step of the interop pipeline.
* **Validation templates** – Required-field definitions, regex patterns, and
  allowed-value lists that power the validation stage.

Each template is stored as canonical JSON under `configs/interop/...` with a
one-click CSV export/import to support analyst workflows.  The edit forms offer
simple row-based tables (blank rows are ignored so removing an entry is as easy
as clearing the segment/field values).

Runtime behaviour:

* Selecting a template in the Interop UI or pipeline causes the corresponding
  rules/checks to be enforced.  When no template is chosen the legacy behaviour
  remains available via the built-in scrubber and basic validator.
* Validation issues surface in the UI alongside the existing `errors`/`warnings`
  view, while de-identification continues to populate the report summary.

Refer to the settings index page for management actions (create, import, export,
delete) and use the per-template editor to fine-tune individual rules.
