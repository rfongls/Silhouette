# Interoperability Overview

Silhouette Core provides end-to-end healthcare interoperability:
- Messaging & Documents: HL7 v2.x, CDA/CCD
- APIs & Resources: FHIR (R4/R5), SMART on FHIR
- Exchanges: IHE XDS.b, Direct Secure Messaging (DSM), HIE/RLS
- Policy & Networks: TEFCA, QHIN workflows
- Admin & Claims: X12 270/271 (eligibility), 278 (prior auth)
- Patient Access: Blue Button 2.0, CCD generation
- Identity & Master Data: PIX/PDQ, MDM entity resolution

## Build Targets
- Parsers: `skills/interoperability.py`
- Connectors: `connectors/hie/*.py`, `connectors/tefca/*.py`, `connectors/dsm/*.py`
- Validators: `validators/hl7.py`, `validators/fhir.py`, `validators/cda.py`
- Tests: `tests/test_interoperability.py`

## Logging & Reporting (Overview)
We log each pipeline step (generate, de‑identify, validate, translate, mllp) as ordered task events inside a run, with content snapshots for lineage. See:
- Data model → `docs/data-model/sqlite-schema.md`
- Audit API → `docs/api/audit.md`
