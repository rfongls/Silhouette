# Interoperability Skill — Usage

The interoperability skill bundles HL7 drafting/sending and FHIR translate/validate helpers.

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
