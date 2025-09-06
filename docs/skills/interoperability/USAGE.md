# Interoperability Skill — Usage

The interoperability skill bundles HL7 drafting/sending and FHIR translate/validate helpers.

## UI Quick Start (no listener required)
Open **Interoperability Dashboard → Quick Start**:
- Choose a trigger (e.g., `VXU_V04`)
- Click **Run Pipeline** to: Draft example HL7 → FHIR Translate → Validate
- KPIs update instantly (Send/Translate/Validate)

## Examples
- **HL7 (downloadable)**: `static/examples/hl7/samples/*.hl7`
- **HL7 (drafter JSON)**: `static/examples/hl7/json/*.json`
  Use the **Example** picker in “Draft & Send HL7” to auto-fill valid content.
- **FHIR bundle**: `static/examples/fhir/bundle.json`
 
## Batch & Watch
- **Send batch**: upload a folder of `.hl7` to MLLP.
- **Translate batch**: upload a folder; optional **Validate after**.
- **Validate Last Translate Output**: validate the most recent translate output.
- **Directory watcher**: start a background loop to watch `in/hl7` and translate (optional validate) to `out/interop/watch`.

## HL7 Analyze
Upload `.hl7` to get quick segment counts (MSH/PID/OBR/OBX/etc.) and sanity-check structure.

## FHIR API (Read)
Provide a base URL and resource path (e.g., `Patient/123`) and an optional Bearer token to fetch a resource for inspection.

## 1) Draft & Send HL7
```python
from skills.hl7_drafter import draft_message, send_message
msg = draft_message("ADT_A01", {"patient_id": "123"})
ack = await send_message("127.0.0.1", 2575, msg)
```

## 2) FHIR Translate
```python
from api.interop import _run_cli
result = _run_cli(["fhir", "translate", "--in-dir", "in", "--out-dir", "out"])
```

## 3) FHIR Validate
```python
from api.interop import _run_cli
result = _run_cli(["fhir", "validate", "--in-dir", "in"])
```

Outputs are written under `out/interop/` by default.
