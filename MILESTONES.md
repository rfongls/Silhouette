
# 🗓️ Milestone: Phase 1 – Bootstrap Survival Core

## Description
Establish the minimal viable Silhouette Core capable of running locally with purpose-aligned behavior and modular extensibility.

## Goals
- Create CLI fallback shell
- Support offline model inference (GGUF)
- Load and apply alignment rules from DSL
- Build module loader interface
- Define initial documentation and CI

## Duration
Recommended duration: 4–6 weeks

## Related Files
- `PHASE_1_ISSUES.md`
- `TODO.md`
- `CONTRIBUTING.md` (to be created)


# 🗓️ Milestone: Phase 2 – Intelligent Runtime

## Description
Introduce foundational logic that allows Silhouette Core to parse user intent, recognize tone, and store recoverable sessions. Add a memory engine with API access and a flexible server interface.

## Goals
- Phrase-based intent recognition
- Tone/emotion parsing
- Memory write + search system
- REST API (FastAPI)
- Full unit tests for each component

## Duration
Recommended duration: 2–3 weeks

## Related Files
- `intent_engine.py`
- `memory_core.py`
- `tone_parser.py`
- `interface_server.py`
- `tests/test_*.py`

---

# 🗓️ Milestone: Phase 3 – Contextual Graph + Autonomy

## Description
Enable deeper conversation modeling by linking memory entries into a graph structure. Empower Codex to autonomously evolve the project using a dev controller and knowledge ingestion pipeline.

## Goals
- Build graph engine linking memory by time, intent, tone
- Enable graph traversal and summarization
- Introduce `codex_controller.py` + `auto_dev.yaml` for self-generating modules
- Create `trainer.py` + `embedding_engine.py` for knowledge ingestion
- Establish `knowledge_store/` as structured input for long-term learning

## Duration
Recommended duration: 3–4 weeks

## Related Files
- `graph_engine.py`
- `trainer.py`, `embedding_engine.py`
- `codex_controller.py`, `auto_dev.yaml`
- `tests/test_graph.py`
