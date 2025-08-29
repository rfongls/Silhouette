# HL7→FHIR Integration — Progress Log (US Core)

**Owner:** Silhouette Core • **Target IG:** US Core (pinned) • **FHIR:** R4 (4.0.1)

Use this doc to track delivery against the Codex handoff phases. Update checkboxes, dates, and commit/PR references as work lands.

---

## At‑a‑Glance Status

* **Current Phase:** 5 — Validation
* **MVP Definition of Done:**
  * ADT^A01 → `Patient`, `Encounter`, `Provenance` (US Core‑valid)
  * ORU^R01 → `Patient`, `Observation`, `DiagnosticReport` (+`Specimen` if present) (US Core‑valid)
  * Dual validation (JSONSchema + HAPI) in CI
  * Conditional upserts verified on sandbox
  * Runbook in `docs/fhir/`

---

## Phase Checklist & Status

### Phase 0 — Preflight & Scaffolding

* [x] Create directories: `config/`, `maps/`, `terminology/`, `validators/`, `scripts/`, `out/{qa,fhir/{ndjson,bundles},deadletter}`  \
  **Commit/PR:** `58eb1e0` • **Date:** 2025‑08‑29
* [x] Add skeleton `silhouette_core/pipelines/hl7_to_fhir.py`  \
  **Commit/PR:** `58eb1e0` • **Date:** 2025‑08‑29
* [x] Wire `silhouette fhir translate` subcommand (help + flags)  \
  **Commit/PR:** `58eb1e0` • **Date:** 2025‑08‑29
* [x] Add HL7 test fixtures (`tests/data/hl7/adt_a01.hl7`, `oru_r01.hl7`)  \
  **Commit/PR:** `58eb1e0` • **Date:** 2025‑08‑29

**Notes/Blockers:** *(none yet)*

---

### Phase 1 — Pin the IG & Package Management

* [x] Create `config/fhir_target.yaml` (package_id, version, fhir_version, default_profiles, terminology)  \
  **Commit/PR:** `58eb1e0` • **Date:** 2025‑08‑29
* [x] Implement `scripts/fhir_packages.py` to prefetch IG packages into `.fhir/packages/`  \
  **Commit/PR:** `c34b83e` • **Date:** 2025‑08‑29
* [x] CI step to assert packages present and versions pinned  \
  **Commit/PR:** `TBD` • **Date:** 2025‑08‑29

**Notes/Blockers:** *(add if tx server or Java availability is an issue)*

---

### Phase 2 — Mapping Framework & Transforms

 * [x] YAML mapping loader (profile, resourcePlan, rules, MustSupport policy)  \
  **Commit/PR:** `89a814c` • **Date:** 2025‑08‑29
* [x] `translators/transforms.py` with unit tests:
  * `ts_to_date`, `ts_to_instant`
  * `pid3_to_identifiers`
  * `name_family_given`
  * `sex_to_gender`
  * `pv1_class_to_code`
  * UCUM helpers
  **Commit/PR:** `2451942` • **Date:** 2025-08-29
 * [x] Ensure each resource sets `meta.profile` from mapping or defaults  \
  **Commit/PR:** `89a814c` • **Date:** 2025‑08‑29

**Notes/Blockers:** *(fill in)*

---

### Phase 3 — Orchestration & Bundle

* [x] Orchestrate pipeline: HL7 ingest → QA → Map → MustSupport → Bundle (transaction) → Provenance → Artifacts  \
  **Commit/PR:** `025c9cb` • **Date:** 2025‑08‑29
* [x] Deterministic `urn:uuid:` `fullUrl`s and conditional upserts (PUT for Patient/Encounter)  \
  **Commit/PR:** `025c9cb` • **Date:** 2025‑08‑29
* [x] CLI flags: `--map`, `--rules`, `--bundle`, `--out`, `--dry-run`, `--server`, `--token`, `--validate`  \
  **Commit/PR:** `025c9cb` • **Date:** 2025‑08‑29

**Notes/Blockers:** *(fill in)*

---

### Phase 4 — Reference Maps (US Core)

* [x] `maps/adt_uscore.yaml` (Patient, Encounter, Provenance)  \
  **Commit/PR:** `89a814c` • **Date:** 2025‑08‑29
* [x] `maps/oru_uscore.yaml` (Patient, Observation[lab], DiagnosticReport, Specimen, Provenance)  \\
  **Commit/PR:** `TBD` • **Date:** 2025-08-29
* [x] Snapshot tests (`tests/data/fhir/gold/*.json`)  \\
  **Commit/PR:** `TBD` • **Date:** 2025-08-29

**Notes/Blockers:** *(fill in)*

---

### Phase 5 — Validation (JSONSchema + HAPI + $validate opt‑in)

* [ ] Local JSONSchema shape validation wired
* [ ] `validators/hapi_cli.py` to run HAPI Validator with pinned IGs
* [ ] CLI: `silhouette fhir validate --in … --hapi`
* [ ] Optional remote `$validate` before posting

**Notes/Blockers:** *(fill in)*

---

### Phase 6 — Terminology MVP

* [ ] `terminology/sex_map.csv`, `pv1_class.csv`, `loinc_map.csv`
* [ ] Lookup helpers + metrics emission on misses

**Notes/Blockers:** *(fill in)*

---

### Phase 7 — Posting & Observability

* [ ] Transaction POST/PUT logic with retries & backoff
* [ ] Dead‑letter writes on failure (request + response)
* [ ] Metrics CSV (`out/metrics.csv`)
* [ ] Structured logs per message

**Notes/Blockers:** *(fill in)*

---

### Phase 8 — CI/CD & Quality Gates

* [ ] CI: unit tests + translation on fixtures + HAPI validation
* [ ] Cache FHIR packages; pin Java/HAPI versions
* [ ] Upload `out/*` artifacts on PRs

**Notes/Blockers:** *(fill in)*

---

### Phase 9 — Docs & Runbook

* [ ] Developer guide: mapping authoring conventions, transforms catalog, MustSupport policy
* [ ] Ops runbook: config, posting, validator errors, tx‑miss triage
* [ ] Examples in README and `docs/fhir/`

**Notes/Blockers:** *(fill in)*

---

## Commit/PR Mapping (Append as You Merge)

* PR #TBD — "Scaffold HL7→FHIR pipeline & CLI"; **Phase(s):** 0,1 • **Merged:** TBD • **SHA:** `58eb1e0`
* PR # — "Mapping YAML loader + ADT map"; **Phase(s):** 2,4 • **Merged:** TBD • **SHA:** `89a814c`
* PR # — "Orchestrate HL7→FHIR pipeline"; **Phase(s):** 3 • **Merged:** TBD • **SHA:** `025c9cb`
* PR # — "ADT US Core mapping + tests"; **Phase(s):** 4,5 • **Merged:** TBD • **SHA:**
* PR # — "ORU US Core mapping + tests"; **Phase(s):** 4,5 • **Merged:** TBD • **SHA:**
* PR # — "Posting + observability"; **Phase(s):** 7 • **Merged:** TBD • **SHA:**

---

## Known Risks & Mitigations

* **IG drift** → Pin and add a scheduled job to check latest; open issue w/ diff
* **Terminology gaps** → Log tx‑miss; expand maps iteratively
* **Ambiguous HL7 fields** → Prefer conservative mapping + `dataAbsentReason` per profile rules

---

## Triage / Backlog

Use this section for bugs, profile violations, and work items that pop up during validation.

* [ ] *(example)* ORU: OBX‑5 units missing UCUM → add defaulting rule for specific LOINC codes
* [ ] *(example)* ADT: PID‑3 OID mapping to URI for assigner → introduce org URI registry

