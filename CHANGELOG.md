# Changelog

All notable changes to this project will be documented here.

## [Unreleased]

### Added
- CLI REPL now creates structured logs and reload events
- Intent engine, tone parser, memory writer
- FastAPI server with intent/tone/memory endpoints
- Graph engine to link and summarize memory nodes
- Codex controller + auto_dev.yaml for automated dev cycles
- trainer.py and embedding_engine.py for knowledge ingestion
- Full project documentation suite (7 guides total)

### Changed
- Updated `cli/main.py` to support `:reload`, `:modules`, and session-based logging
- CI workflow modified to allow non-blocking lint feedback

### Tests
- New: `test_intent.py`, `test_memory.py`, `test_tone.py`, `test_interface.py`, `test_graph.py`
- Base memory and graph test coverage above 90%
