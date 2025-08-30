# FHIR Developer Guide

This guide covers conventions for extending the HL7→FHIR pipeline.

## Mapping authoring conventions

* Use YAML maps under `maps/` to describe how HL7 segments populate FHIR fields.
* Each rule lists an `hl7_path`, an output `fhir_path`, and an optional `transform`.
* HL7 field references use the `SEG.FLD` syntax with `|` to pass multiple
  arguments to a transform.
* Keep maps deterministic: avoid side effects inside transforms and prefer
  explicit parameter order.

## Transforms catalog

Reusable helpers live in `translators/transforms.py`.

* Functions are pure and accept primitives plus an optional `metrics` dict.
* The pipeline auto‑detects whether a transform accepts `metrics` and passes it
  when present.
* Common transforms: `ts_to_date`, `sex_to_gender`, `pv1_class_to_code`,
  `obx_value_to_valuex`.

## MustSupport policy

Profiles often mark elements as **MustSupport**. Our approach:

1. If data is present but invalid, omit the element and increment `tx-miss`.
2. Missing required elements route the message to dead‑letter with a concise
   reason.
3. Let validators and runbooks surface downstream issues; transforms should not
   raise unless the input is unusable.

## Adding new message types

1. Create a new map (e.g., `maps/adt_uscore.yaml`).
2. Author translation rules with existing transforms where possible.
3. Add fixtures under `tests/data/hl7/` and expected FHIR bundles under
   `tests/data/fhir/gold/`.
4. Register the map in integration tests and update the runbook.

