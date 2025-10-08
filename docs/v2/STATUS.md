# Engine V2 — Phase Status Log

This document is updated **with each PR** that changes the Engine V2 code or UI. It tracks what was implemented and when.

> Timestamps are ISO-8601 (UTC). If you prefer local time in commits, adjust before merging.

---

## Phase 0 — Skeleton

**Status:** ✅ Completed  
**Implemented:** 2025-10-06T00:00:00Z
**Scope:**
- Contracts for adapters, operators, router, and sinks
- Pipeline spec validation (`/api/engine/pipelines/validate`)
- Insights DB + summary endpoint (`/api/insights/summary`)
- Feature-flagged UI entry “Engine (Beta)” with Insights table
- Registry diagnostics endpoint (`/api/engine/registry`)

**Notes:**
- Registry is guaranteed via `engine.plugins` side-effect import.
- Minimal built-ins: `sequence` adapter, `echo` operator, `memory` sink.
- Validation rejects unknown adapters/operators/sinks with a 400 response to match docs.

---

## Phase 0.5 — Demo Runs

**Status:** ✅ Completed  
**Implemented:** 2025-10-06T00:00:00Z
**Scope:**
- Execute a pipeline on demand (`POST /api/engine/pipelines/run`)
- Optional persistence into insights store
- UI button “Run demo pipeline” to exercise end-to-end loop

**Notes:**
- Keeps run history visible in Insights without background workers.
- `/api/engine/health` now reports version `phase0.5` to align with the demo run capability.

---

## Phase 1 — Adapters & Operators (In Progress)

**Status:** 🚧 Planned / In progress  
**Target:** Wire V1 validations/de-identify as operators; add file/MLLP adapters  
**PR checklist:** Update this file on merge with:
1. What shipped (operators/adapters/fields)
2. Any config names that mirror V1 (to ensure uniformity)
3. Implementation timestamp (UTC)
