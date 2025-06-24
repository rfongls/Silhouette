# Changelog

All notable changes to this project will be documented here.

## [Unreleased]

### Added 
- (reserved for upcoming Phase 9 work)

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

## [Phase 6] - Scalable Execution

### Added
- `performance_profiler.py` to capture CPU, memory and I/O metrics  
- `config/performance.yml` defines edge, mid-tier and core profiles  
- `module_executor.py` executes modules in parallel using a priority queue  
- `distributed_executor.py` stub lays groundwork for multi-node execution  
- `offline_mode.load_throttle` delays tasks when system load is high  
- Tests for concurrent and distributed execution stubs  

### Changed
- Documentation updated with distributed execution protocol  

## [Phase 7] – Multi-Agent Interface & Messaging

### Added
- `agent_controller.py` to manage agent processes (spawn, fork, merge, shutdown)  
- `agent_messaging.py` for socket- or HTTP-based inter-agent communication  
- `memory_merge.py` for diffing and merging agent memory stores  
- CLI commands under `:agent` in `cli/main.py`: `spawn`, `fork`, `merge`, `list`, `export`, `import`, `audit`  
- `docs/agent_api.md` documenting the inter-agent message schema  
- `docs/agent_scenarios.md` with example multi-agent workflows  
- `tests/test_agent_controller.py` and `tests/test_agent_messaging.py` for agent functionality  

### Changed
- `cli/main.py` updated to integrate multi-agent commands  
- `README.md` quickstart extended with multi-agent usage  

## [Phase 8] – Self-Reflective Monitoring

### Added
- `drift_detector.py` to detect drift in tone, intent, and behavior  
- `config/drift.yml` schema for drift metrics and thresholds  
- `session_summarizer.py` to generate human-readable session summaries  
- `persona_audit.py` to validate memory entries against `persona.dsl` deny rules  
- Extended `selfcheck_engine.py` with `--full` flag to run drift detection, session summary, and persona audits  
- CLI commands `:drift-report`, `:summary`, and `:persona-audit` in `cli/main.py`  
- `docs/monitoring.md` overview of self-reflective monitoring workflow  
- `docs/examples/drift_config.yml` example configuration for drift metrics  
- `tests/test_drift_detector.py` for drift detection logic  
- `tests/test_cli_integration.py` updated with monitoring command tests  

### Changed
- `cli/main.py` updated to support new monitoring commands  
- `README.md` extended to include self-reflective monitoring usage  
