# FHIR Ops Runbook

Operational notes for running the HL7→FHIR pipeline.

## Configuration

* Default settings live in `config/` – copy and adjust for your environment.
* Set `FHIR_TOKEN` for authenticated servers; leave unset for public sandboxes.
* Package cache: ensure `.fhir/packages` is writable so HAPI can reuse IGs.

## Posting modes

* **Dry run** (`--dry-run`): generate artifacts and metrics without hitting a server.
* **Post**: provide `--server <URL>` and optional `--token` to upsert resources.
* Conditional upserts are preserved for Patient/Encounter when identifiers exist.

## Validator usage

* Local: `silhouette fhir validate --in out/fhir/ndjson/*.ndjson --hapi`.
* Server: add `--server` and `--validate` to call `$validate` before posting.
* HAPI versions and IGs are pinned in `config/fhir_target.yaml`.

## tx-miss triage

`tx-miss` counts unresolved terminology or mapping gaps.

1. Inspect `out/qa/metrics.csv` for non‑zero `txMisses`.
2. Review logs for the specific segments and update terminology tables or maps.

## Dead-letter handling

Failed validations or posts write request/response pairs under `out/deadletter/`.

* `<messageId>_request.json` – the bundle that failed.
* `<messageId>_response.json` – server or validator error details.
* After fixes, rerun the pipeline; successful posts remove previous dead letters.

