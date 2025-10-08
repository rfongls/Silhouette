# Engine V2 Overview

The Engine runtime is a companion to the Interop tooling, enabling configurable pipelines composed of adapters, operators, an optional router, and sinks. Phase 0 delivers the skeleton necessary to validate specs and persist operator results for UI insights.

**Last updated:** 2025-10-08 (UTC)

## Runtime

* `engine/contracts.py` defines the core dataclasses (`Message`, `Issue`, `Result`) and ABCs (`Adapter`, `Operator`, `Sink`).
* `engine/registry.py` tracks named factories for adapters/operators/sinks.
* `engine/runtime.py` assembles a pipeline from a `PipelineSpec`, streams messages from the adapter, runs each operator in sequence, then broadcasts results to all sinks. Persistence can be attached via an async callback.
* Built-in helpers (`engine/builtins.py`) register a `sequence` adapter, `echo` operator, and `memory` sink to support the minimal example pipeline. Phase 0.5 adds stub implementations for a `file` adapter, `mllp` adapter placeholder, and `validate-hl7` / `deidentify` operators so the registry reflects the upcoming work.

## Pipeline Specification

`engine/spec.py` uses Pydantic to validate YAML specs. A pipeline contains:

```yaml
version: 1
name: demo-sequence
adapter:
  type: sequence
  config: {...}
operators:
  - type: echo
    config: {...}
router:
  strategy: broadcast
sinks:
  - type: memory
    config: {...}
metadata:
  owner: interoperability
```

Use `POST /api/engine/pipelines/validate` to normalize incoming YAML and ensure registered components exist.

To execute a pipeline on demand, call `POST /api/engine/pipelines/run`. The endpoint accepts the YAML spec, optional `max_messages`, and a `persist` flag. When persistence is enabled the runtime creates a run record, writes each `Result` to the insights store, and returns the normalized spec, counts by severity, and run identifier.

## Diagnostics

* `GET /api/engine/registry` – returns the adapters, operators, and sinks currently registered with the runtime. Use this to confirm built-ins (and any locally developed components) are available once the app starts.

## Insights Flow

Pipelines (or seed scripts) record `Result` objects into the insights store. Each run captures the pipeline name, messages processed, and emitted issues grouped by severity. The UI consumes `GET /api/insights/summary` to render run totals and top findings. The Engine (Beta) page now includes a **Run demo pipeline** action that posts the minimal example spec to the run endpoint and refreshes the summary table so you can see the persistence loop end-to-end.
