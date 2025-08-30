# HL7 v2 → FHIR Integration — Next Phases (Detailed, with Checkboxes)

This plan drives a **US Core–compliant** HL7 v2 → FHIR pipeline using your existing HL7 QA tool and the new FHIR skill.

> **Note:** When implementing any item, also update [`docs/fhir_progress.md`](fhir_progress.md) to reflect completion.
>
> Legend per item: **Implement** (what to build), **Test** (how to verify), **DoD** (Definition of Done).  
> Items already completed per your commit summaries are pre-checked.

---

## Phase 0 — Preflight & Scaffolding ✅
- [x] Create directories for configuration, mappings, terminology, validators, scripts and output artifacts (`config/`, `maps/`, `terminology/`, `validators/`, `scripts/`, `out/{qa,fhir/{ndjson,bundles},deadletter}`, `tests/data/hl7/`).
  - **DoD:** Directories exist with `.gitkeep` as needed.
- [x] Add `config/fhir_target.yaml` with pinned package/version and default profile URLs.
  - **DoD:** File loads (YAML parse) with keys: `package_id`, `package_version`, `fhir_version`, `default_profiles`, `terminology`.
- [x] Add example HL7 fixtures under `tests/data/hl7/` (ADT^A01, ORU^R01).
  - **DoD:** Files present and readable by the pipeline.
- [x] Add skeleton pipeline `silhouette_core/pipelines/hl7_to_fhir.py` and wire a no-op path through the CLI (`silhouette_core/cli.py`).
  - **DoD:** `silhouette fhir translate --help` prints flags without error.

---

## Phase 1 — Pin the IG & Package Management ✅
- [x] Implement `scripts/fhir_packages.py` to prefetch packages into `.fhir/packages/` cache. _(commit: `c34b83e`)_
  - **Test:** Run script; verify cache directory populated; re-runs are no-ops.
  - **DoD:** Cache contains `<package>#<version>` folders; mismatches cause a clear error.
- [x] Support configuration for package IDs, FHIR version, default profiles and terminology (via `config/fhir_target.yaml`).
  - **DoD:** US Core defaults set (Patient/Encounter/Observation canonical URLs).
- [x] Add CI step to assert packages are present with exact versions.
  - **Implement:** In CI, run `python scripts/fhir_packages.py --assert`.
  - **Test:** Break version intentionally → CI fails.
  - **DoD:** CI fails on drift; logs show expected vs actual.

---

## Phase 2 — Mapping Framework & Transforms ✅
- [x] Extend translator to ingest **YAML mapping profiles** declaring target profile, resource plan, rules and MustSupport policy.
  - **Implement:** `translators/mapping_loader.py` with `MappingSpec`, `ResourcePlan`, `MappingRule` dataclasses; optional `extends` merge.
  - **Test:** Unit test loading minimal map + `extends`.
  - **DoD:** Loader returns typed objects; helpful errors on missing keys.
- [x] Implement transform helpers in `translators/transforms.py` (`ts_to_date`, `ts_to_datetime`, `pid3_to_identifiers`, `name_family_given`, `sex_to_gender`, `pv1_class_to_code`, UCUM `build_quantity`).
  - **Add stubs for ORU (Phase 4 will fill):** `obx_cwe_to_codeableconcept`, `obx_status_to_obs_status`, `obr_status_to_report_status`, `obx_value_to_valuex`, `spm_cwe_to_codeableconcept`, `to_oid_uri`.
  - **Test:** `tests/test_transforms.py`—TS precision, gender edges, PV1 class mapping, PID-3 OID vs namespace, UCUM quantity.
  - **DoD:** All transform tests pass.
- [x] Ensure every resource sets **`meta.profile`** from mapping or configuration defaults.
  - **Implement:** After creating each resource, set `meta.profile=[...]`.
  - **Test:** Translate ADT; inspect JSON for `meta.profile`.
  - **DoD:** No resource emitted without `meta.profile`.

---

## Phase 3 — Pipeline Orchestration & CLI ✅
- [x] Build orchestration for **ingest → QA → map → bundle → output**.
  - **Implement:** Deterministic `MessageId`, stable `urn:uuid:` `fullUrl`s; Provenance referencing all entries + source message; conditional upserts (PUT Patient; PUT Encounter if identifier else POST).
  - **Test:** Translate `tests/data/hl7/adt_a01.hl7`; verify artifacts.
  - **DoD:** Bundle, NDJSON, Provenance present; upserts applied when identifiers exist.
- [x] Implement CLI flags for translation, validation and posting.
  - **Implement:** `--in`, `--map`, `--rules`, `--bundle`, `--out`, `--dry-run`, `--server`, `--token`, `--validate`.
  - **DoD:** Translate path wired; validate/post flags recognized (server call can be gated).
- [x] Write NDJSON and Bundle JSON artifacts to `out/`.
  - **DoD:** `out/qa/*.jsonl`, `out/fhir/ndjson/*.ndjson`, `out/fhir/bundles/*.json` appear per message.

---

## Phase 4 — Reference Maps (US Core) ✅
- [x] Add `maps/adt_uscore.yaml` (Patient, Encounter, Provenance) with MustSupport handling and conditional upserts.
  - **Implement:** Map PID identifiers/name/DOB/gender; PV1 class, visit number, admit/discharge times; `must_support` policy; `conditional` templates.
  - **Test:** ADT fixture → Patient+Encounter; Patient.identifier type MR (v2-0203); Encounter.class ActCode; `period.start/end` when present.
  - **DoD:** Bundle contains US Core-profiled Patient/Encounter.
- [x] Add `maps/oru_uscore.yaml` (Patient, DiagnosticReport, Observation[labs], Specimen).
  - **Implement:** OBR/OBX/SPM mapping; `Observation.value[x]` builder (UCUM for quantities); category `laboratory`.
  - **Test:** ORU fixture → DiagnosticReport with linked Observations via `result`; Observations have `status`, `code`, `effectiveDateTime`, and `value[x]`.
  - **DoD:** Bundle contains US Core lab Observation(s) + DiagnosticReport.
- [x] Snapshot tests comparing generated JSON to gold files in `tests/data/fhir/`.
  - **Implement:** Gold files: `tests/data/fhir/gold/adt_a01_bundle.json`, `.../oru_r01_bundle.json`; snapshot compare (ignore volatile timestamps).
  - **DoD:** Tests pass; diffs highlight mapping regressions.

---

## Phase 5 — Validation ✅
- [x] Local JSON Schema checks.
  - **Implement:** Lightweight shape validator; clear path to offending element.
  - **Test:** Introduce invalid field; expect failure.
  - **DoD:** Shape errors caught pre-HAPI.
- [x] HAPI FHIR validation via `validators/hapi_cli.py`.
  - **Implement:** Wrapper to run validator JAR with `-ig hl7.fhir.us.core#<version>` using local `.fhir/packages/`.
  - **Env:** Require `JAVA_HOME`; soft-fail with guidance if missing.
  - **Test:** `silhouette fhir validate --in out/fhir/ndjson/*.ndjson --hapi`.
  - **DoD:** Non-zero exit on profile violations; concise errors with pointers.
- [x] CLI flag `silhouette fhir validate` to run validators on generated resources.
  - **DoD:** Invokes local and/or HAPI checks as requested.
- [x] Document validation pipeline in `docs/fhir/validation.md`.
  - **DoD:** Runbook outlines local, HAPI, and server-side validation commands.

---

## Phase 6 — Terminology MVP
- > **Reminder:** Once these items are implemented, update [`docs/fhir_progress.md`](fhir_progress.md).
- [x] Add lookup tables under `terminology/` for gender, encounter class and LOINC mappings.
  - **Implement:** Create `sex_map.csv` (`v2,admin_gender`), `pv1_class.csv` (`v2,act_code`), `loinc_map.csv` (`obx3_code,system,display,default_ucum_code,default_unit_text`).
  - **Test:** Load each table via terminology loader; known codes resolve, unknown codes return `None`.
  - **DoD:** Files exist; loader reads into dicts.
- [x] Add lookup helpers emitting metrics when codes are missing.
  - **Implement:** Helpers in `translators/transforms.py`; emit **tx-miss** metric once per unknown code.
  - **Test:** Translate sample HL7 with known and unknown codes; ensure metrics increment only for misses.
  - **DoD:** Observations include UCUM when known; misses recorded.

---

## Phase 7 — Posting & Observability ✅

- [x] **HTTP posting with retries**
  - Implement `silhouette_core/posting.py`:
    - `post_transaction(bundle: dict, server: str, token: str, timeout=20, max_retries=3)`
    - Retry on 429/5xx with exponential backoff + jitter; log attempt count and final outcome.
    - Write failures to `out/deadletter/` as `<messageId>_request.json` and `<messageId>_response.json`.
  - Acceptance: simulated 429 → retried; 2xx → success recorded.

- [x] **Conditional upserts preserved**
  - Keep `PUT Patient?identifier=...` and `PUT Encounter?identifier=...` when IDs exist; `POST` otherwise.
  - Acceptance: sandbox shows idempotent Patient/Encounter upserts across multiple runs.

- [x] **Metrics CSV**
  - Create `out/metrics.csv` with headers:
    ```
    messageId,type,qaStatus,fhirCount,posted,latencyMs,txMisses,postedCount,deadLetter
    ```
  - Append one row per message; `txMisses` is the per-message total from transforms.
  - Acceptance: file grows deterministically; values match logs.

- [x] **Structured logs**
  - Log one JSON line per message:
    ```
    {"ts":"<iso>", "messageId":"...", "phase":"post", "posted":true, "status":201, "txMisses":2, "resourceCounts":{"Patient":1,"Observation":3}}
    ```
  - Acceptance: logs parsable by jq; errors include server response summary.

- [x] **Dry-run safety**
  - If `--dry-run`, skip posting but still produce artifacts + metrics.
  - Acceptance: run with and without `--dry-run`; only the latter hits server.

- [x] **CLI wiring**
  - `silhouette fhir translate ... --server <URL> --token $FHIR_TOKEN` posts bundles unless `--dry-run`.
  - `--validate` triggers server-side `$validate` before POST; failures route to dead-letter.
  - Acceptance: bad resources fail `$validate`, do not post, and are captured in dead-letter.

---

## Phase 8 — CI/CD & Quality Gates ✅
- [x] CI job runs unit tests, sample translations and HAPI validation with cached packages.
  - **Steps:**
    1. Setup Python + Java.
    2. `python scripts/fhir_packages.py --assert`.
    3. `pytest -q`.
    4. `silhouette fhir translate --in tests/data/hl7/*.hl7 --map maps/adt_uscore.yaml --bundle transaction --out out/ --dry-run` (and ORU).
    5. `silhouette fhir validate --in out/fhir/ndjson/*.ndjson --hapi`.
    6. Upload `out/` artifacts.
  - **DoD:** CI fails on mapping/validation regressions; artifacts attached to PR.
- [x] Upload QA and FHIR artifacts on pull requests.
  - **DoD:** `out/qa/*`, `out/fhir/*` visible in PR checks.

---

## Phase 9 — Docs & Runbook ✅
- [x] Author **developer guide** (`docs/fhir/developer_guide.md`).
  - Mapping authoring conventions; transforms catalog; MustSupport policy; adding new message types.
  - **DoD:** Doc includes code snippets and examples.
- [x] Author **ops runbook** (`docs/fhir/runbook.md`).
  - Config; posting modes; validator usage; tx-miss triage; dead-letter handling.
  - **DoD:** A new engineer can run ADT→FHIR in <10 minutes following docs.
- [x] Add **CLI examples** in README.
  - **DoD:** Copy-paste commands for translate (dry-run), validate, post.

---

## Milestone Checklist
- [ ] **ADT^A01**: US Core–valid Patient + Encounter + Provenance (local + HAPI pass).
- [ ] **ORU^R01**: US Core–valid Observation(s) + DiagnosticReport (+Specimen when present) + Provenance (local + HAPI pass).
- [ ] Dual validation (JSONSchema + HAPI) wired in CI.
- [ ] Conditional upserts verified on a sandbox server.
- [ ] Runbook/docs published under `docs/fhir/`.

---

## Notes / Guardrails
- Prefer **`dateTime`** when timezone is unknown; use **`instant`** only when TZ present *and* the element requires it.
- **Encounter conditional upsert** only when a stable identifier (e.g., PV1-19) is present; otherwise POST Encounter.
- Use **`dataAbsentReason`** only where profiles allow; otherwise omit the element and dead-letter with a MustSupport reason.
---

## Phase 10 — Orders (ORM/OML → ServiceRequest)
- [x] Map **ORM/OML** orders to **ServiceRequest** (+ optional **Task** for workflow).
  - **Implement:** `maps/orm_uscore.yaml` with placer/filler numbers (ORC/OBR), code (OBR-4), priority, reason, requester, performer.
  - **Linkage:** Results reference orders via `DiagnosticReport.basedOn` / `Observation.basedOn`.
  - **Identifiers:** Define conditional upsert keys: placer/filler order identifiers with **real system URIs**.
  - **DoD:** ServiceRequest created/updated; ORU bundles reference it; HAPI passes.

## Phase 11 — Scheduling (SIU → Appointment)
- [x] Map **SIU** events to **Appointment** (+ **Schedule/Slot** optional).
  - **Implement:** `maps/siu_uscore.yaml` with participants (**Patient**, **PractitionerRole**, **Location**, **Organization**), start/end, status (`booked`, `cancelled`, `noshow`).
  - **Identifiers:** Stable business keys for conditional upsert (placer schedule/appointment ID).
  - **DoD:** Appointment created/updated per triggers (book/update/cancel); HAPI passes.

## Phase 12 — Immunizations (VXU → Immunization)
- [x] Map **VXU^V04** to **Immunization**.
  - **Implement:** `maps/vxu_uscore.yaml` with CVX code, lot/expiry, occurrence date, performer, route/site.
  - **Identifiers:** vaccine record ID to prevent dupes; organization/performer references.
  - **DoD:** Immunization upserts validate; snapshot tests green.

## Phase 13 — Pharmacy (RDE/RXO/RXE → Medication*)
- [x] Map order/dispense/admin:
  - **MedicationRequest** (order intent/status), **MedicationDispense**, **MedicationAdministration**.
  - **Implement:** `maps/rde_uscore.yaml` covering medication coding (RxNorm where available), dose/route/frequency, quantity, status transitions (new/change/cancel).
  - **DoD:** Resources emitted and linked to Patient/Encounter; HAPI passes core checks.

## Phase 14 — Documents (MDM → DocumentReference/Binary) — *NEW*
- [ ] Map **MDM** add/update to **DocumentReference** (+ **Binary**).
  - **Implement:** `maps/mdm_uscore.yaml` with type (LOINC/SNOMED as available), author, facility, creation date, attachment (contentType, hash, size).
  - **Versioning:** New version on updates; maintain master ID for conditional upsert.
  - **DoD:** DocumentReference + Binary validate; snapshot tests green.

## Phase 15 — Charges/Accounts (DFT/BAR → ChargeItem/Account) — *NEW*
- [ ] Map **DFT/BAR** to **ChargeItem** (+ **Account**; optional **Claim** for payer flows).
  - **Implement:** `maps/dft_uscore.yaml` with code, amount, subject (Patient), context (Encounter), account linkage.
  - **DoD:** Charge items persist and link; basic validation passes.

## Phase 16 — ADT Extensions & Merge/Corrections — *NEW*
- [ ] Handle **A02/A03/A08/A11/A13** Encounter state updates; **A40** merges.
  - **Implement:** State machine: transfer/discharge → `Encounter.status/location/period`; cancel → `status=cancelled`; updates → PUT.
  - **Merge:** Set old **Patient.active=false** and `Patient.link.type = replaced-by` → new Patient.
  - **ORU corrections:** `Observation.status=corrected` with Provenance.
  - **DoD:** Snapshot fixtures for each trigger; HAPI passes.

## Phase 17 — Reference Entities & Identifier Registry — *NEW*
- [ ] Upsert **Organization**, **Practitioner**, **PractitionerRole**, **Location** and reference them from Encounter/DR/Observation/ServiceRequest/Appointment.
  - **Implement:** `config/identifier_systems.yaml` for canonical URIs (MRN, visit, order, specimen, organization, practitioner, location).
  - **DoD:** All emitted resources use real system URIs; references resolve; validation passes.

## Phase 18 — Partner IG Profiles & Validation — *NEW*
- [ ] Support partner-specific IG packages and `$validate` against them.
  - **Implement:** `config/partners/<name>.yaml` (IG list, profile overrides, MustSupport rules).
  - **CLI:** `--partner <name>` toggles IG set and schema expectations.
  - **DoD:** HAPI runs with partner IG; CI matrix executes per partner config.

## Phase 19 — Messaging Mode (optional) — *NEW*
- [ ] Add **Bundle.type=message** support with **MessageHeader** for sites that require messaging.
  - **Implement:** `--message-mode` flag; map MSH-9 triggers to MessageHeader `event`.
  - **DoD:** Message bundles validate; posting path remains transaction by default.
