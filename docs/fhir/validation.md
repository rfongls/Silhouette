# Validation Runbook

This pipeline validates FHIR resources at three levels:

1. **Local shape checks** — cheap, offline
   - JSON Schema + Pydantic to catch type/shape errors early.
   - Runs *before* bundle creation during `translate`, and can be run independently via `validate`.

2. **HAPI FHIR Validator CLI** — profile conformance
   - Uses pinned IG packages from our local cache.
   - Validates that `meta.profile` and MustSupport elements conform to **US Core**.

3. **Server-side `$validate`** — target server’s rules
   - Optional step to ask the destination server to validate the artifacts it would accept.

---

## Commands

### Validate NDJSON locally (shape) + HAPI
```bash
silhouette fhir validate \
  --in out/fhir/ndjson/*.ndjson \
  --hapi \
  --fhir-version 4.0.1 \
  --ig hl7.fhir.us.core#6.1.0
```

### Validate a Bundle JSON (full transaction)

```bash
silhouette fhir validate \
  --in out/fhir/bundles/adt_a01.json \
  --hapi \
  --fhir-version 4.0.1 \
  --ig hl7.fhir.us.core#6.1.0
```

### Validate against a FHIR server’s `$validate`

```bash
silhouette fhir validate \
  --in out/fhir/bundles/oru_r01.json \
  --server https://<your-sandbox>/fhir \
  --token $FHIR_TOKEN \
  --validate
```

> Notes
>
> * `--hapi` requires Java; set `JAVA_HOME` or ensure `java` is on PATH.
> * `--ig` and `--fhir-version` default to values in `config/fhir_target.yaml` if omitted.
> * Validation returns non-zero exit codes on errors; CI fails accordingly.

---

## What we validate

* **All resources** must set `meta.profile` to a canonical URL (e.g., US Core Patient).
* **Observation (labs):** `category=laboratory`, proper `value[x]` (Quantity with UCUM when numeric), `code` (prefer LOINC), `status`.
* **DiagnosticReport:** `code`, `status`, `result[]` links to Observations.
* **Encounter:** `class` (v3-ActCode) when available; omit if unknown.
* **Patient:** identifier (v2-0203 MR type), name, gender, birthDate.
* **Specimen:** base FHIR Specimen profile is acceptable unless an IG requires otherwise.

---

## HAPI CLI wrapper (internals)

* Enforces:

  * `-version 4.0.1` (FHIR R4)
  * `-ig hl7.fhir.us.core#<version>` and core dependencies from the local `.fhir/packages/` cache
* Returns:

  * Exit code `0` on success, non-zero on errors
  * Parsed summary: error count, warning count, offending resource pointers
* Options:

  * `--hapi-args` to pass through extra flags (e.g., to adjust terminology behavior)

---

## Troubleshooting

* **“Unknown profile”** → Ensure `meta.profile` is set and IG version matches `config/fhir_target.yaml`.
* **Terminology timeouts** → Prefer local package cache; if a terminology server is required, configure its URL in `config/fhir_target.yaml` and retry.
* **NDJSON issues** → Ensure one JSON object per line; remove trailing commas; skip blank lines.
* **Snapshot diffs** → Confirm that dynamic fields (e.g., timestamps) are masked in tests only, not in validation.

