# Engine V2 Overview

The Engine runtime is a companion to the Interop tooling, enabling configurable pipelines composed of adapters, operators, an optional router, and sinks. Phase 0 delivers the skeleton necessary to validate specs and persist operator results for UI insights.

## Runtime

* `engine/contracts.py` defines the core dataclasses (`Message`, `Issue`, `Result`) and ABCs (`Adapter`, `Operator`, `Sink`).
* `engine/registry.py` tracks named factories for adapters/operators/sinks.
* `engine/runtime.py` assembles a pipeline from a `PipelineSpec`, streams messages from the adapter, runs each operator in sequence, then broadcasts results to all sinks. Persistence can be attached via an async callback.
* Built-in helpers (`engine/builtins.py`) register a `sequence` adapter, `echo` operator, and `memory` sink to support the minimal example pipeline.

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

## Insights Flow

Pipelines (or seed scripts) record `Result` objects into the insights store. Each run captures the pipeline name, messages processed, and emitted issues grouped by severity. The UI consumes `GET /api/insights/summary` to render run totals and top findings.
