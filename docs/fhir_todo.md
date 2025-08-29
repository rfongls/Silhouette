# HL7 v2 → FHIR Integration — Next Phases

This TODO list tracks the next phases for building the FHIR skill and integrating it with the existing HL7 tooling. Each phase delivers incremental functionality toward a US Core–compliant HL7 v2 to FHIR pipeline.

## Phase 0 — Preflight & Scaffolding
- [ ] Create directories for configuration, mappings, terminology, validators, scripts and output artifacts.
- [ ] Add `config/fhir_target.yaml` with pinned package/version and default profile URLs.
- [ ] Add example HL7 fixtures under `tests/data/hl7/` (ADT^A01, ORU^R01).
- [ ] Add skeleton pipeline `silhouette_core/pipelines/hl7_to_fhir.py` and wire a no-op path through the CLI.

## Phase 1 — Pin the IG & Package Management
- [ ] Implement `scripts/fhir_packages.py` to prefetch packages into `.fhir/packages/` cache.
- [ ] Support configuration for package IDs, FHIR version, default profiles and terminology.
- [ ] Add CI step to assert packages are present with exact versions.

## Phase 2 — Mapping Framework & Transforms
- [ ] Extend translator to ingest YAML mapping profiles declaring target profile, resource plan, rules and MustSupport policy.
- [ ] Implement transform helpers in `translators/transforms.py` (`ts_to_date`, `ts_to_instant`, `pid3_to_identifiers`, `name_family_given`, `sex_to_gender`, `pv1_class_to_code`, UCUM helpers).
- [ ] Ensure `meta.profile` is set from mapping or configuration defaults.

## Phase 3 — Pipeline Orchestration & CLI
- [ ] Build `hl7_to_fhir.py` orchestration for ingest → QA → map → bundle → output.
- [ ] Implement CLI flags for translation, validation and posting.
- [ ] Write NDJSON and Bundle JSON artifacts to `out/`.

## Phase 4 — Reference Maps (US Core)
- [ ] Add `maps/adt_uscore.yaml` and `maps/oru_uscore.yaml` with MustSupport handling and conditional upserts.
- [ ] Snapshot tests comparing generated JSON to gold files in `tests/data/fhir/`.

## Phase 5 — Validation
- [ ] Local JSON Schema checks and HAPI FHIR validation via `validators/hapi_cli.py`.
- [ ] CLI flag `silhouette fhir validate` to run validators on generated resources.

## Phase 6 — Terminology MVP
- [ ] Add lookup tables under `terminology/` for gender, encounter class and LOINC mappings.
- [ ] Add lookup helpers emitting metrics when codes are missing.

## Phase 7 — Posting & Observability
- [ ] Support posting transaction Bundles with conditional upserts and retries.
- [ ] Emit metrics CSV and structured logs; dead-letter failed requests.

## Phase 8 — CI/CD & Quality Gates
- [ ] CI job runs unit tests, sample translations and HAPI validation with cached packages.
- [ ] Upload QA and FHIR artifacts on pull requests.

## Phase 9 — Docs & Runbook
- [ ] Author developer guide, operational runbook and CLI examples under `docs/fhir/`.
- [ ] Ensure a new engineer can run ADT → FHIR in under ten minutes following the docs.

---

### Milestone Checklist
- [ ] ADT^A01 path: US Core valid Patient + Encounter + Provenance.
- [ ] ORU^R01 path: US Core valid Observation + DiagnosticReport (+Specimen when present) + Provenance.
- [ ] Dual validation (JSONSchema + HAPI) wired in CI.
- [ ] Conditional upserts verified on a sandbox server.
- [ ] Runbook/docs published under `docs/fhir/`.

### Next Up After MVP
- [ ] Add site-specific maps and additional message types.
- [ ] Integrate de-identification tooling in the HL7 module prior to FHIR translation.
