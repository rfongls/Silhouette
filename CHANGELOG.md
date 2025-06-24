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

## [Phase 4] - Persona & Embedding Enhancements

### Added
- `alignment_engine.py` parses tone and deny rules from DSL
- `response_engine.py` formats responses and blocks unethical prompts
- `embedding_engine.py` updated with TF-IDF + cosine similarity
- `interface_server.py` now supports `/search` endpoint
- CLI command `:search <query>` for vector-style recall
- `SYSTEM_OVERVIEW.md` created to describe system architecture and recovery
- `test_alignment.py` validates tone and deny behavior

### Changed
- CLI (`main.py`) prompts for file paths during `:restore`
- Response engine now formats based on persona config

## [Phase 5] - Offline-First & Recovery

### Added
- `offline_mode.py` detects offline mode and throttles commands
- `selfcheck_engine.py` verifies required files and memory integrity
- `replay_log_to_memory.py` rebuilds memory from session logs
- CLI commands `:replay` and `:selfcheck`
- Backup works without `cryptography` installed

### Changed
- CLI log files opened with UTF-8 encoding
- Accept `:exit` and `:quit` aliases in the REPL
- Backup status messages use ASCII output

