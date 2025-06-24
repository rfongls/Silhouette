# PHASES.md

Silhouette Core is built in progressive, resilient phases to support modular AI capabilities that can scale from edge devices to full cloud infrastructure.

## ✅ Phase 1 – Bootstrapping & CLI Runtime
- CLI interface with REPL-style commands
- DSL parser loads alignment configuration
- Dynamic module discovery + plug-in loader
- Session logging
- GitHub Actions CI setup (Ruff + Pytest)
- Example module: arithmetic

## ✅ Phase 2 – Foundation of Intelligence
- Intent recognition engine using phrase mapping
- Persistent memory module (JSONL file-based)
- Tone/emotion parsing with keyword rules
- FastAPI server with endpoints:
  - `/intent`, `/tone`, `/memory` (POST), `/memory?q=` (GET)

## ✅ Phase 3 – Contextual Graph Intelligence
- Link memory entries to form a conversation graph
- Enable graph traversal and summarization
- Implement Codex-controlled development flow
- Establish knowledge ingestion and semantic memory indexing

## ✅ Phase 4 – Persona, Search, and CLI Evolution
- DSL-defined behavior/personality profiles
- Tone and deny rule enforcement in responses
- Semantic memory search (TF-IDF + cosine similarity)
- CLI commands `:search`, `:related`, `:summarize`
- RESTful `/search` endpoint
- Response formatting and alignment enforcement

## ⏳ Phase 5 – Offline-First + Recovery
- Run without external dependencies
- Stateless mode with config/log/memory regeneration
- Self-check and integrity verification
- Snapshot memory and logs for backup

## ⏳ Phase 6 – Scaling from Edge to Core

**High-Level Goals:**
- Profiles for edge, mid-tier, and high-capacity deployments  
- Throttle and prioritize modules based on system load  
- Enable parallel or distributed module execution  

**Actionable Subtasks:**
1. **Resource Profiling**  
   - Implement `performance_profiler.py` to capture CPU, memory & I/O metrics per module  
   - Define `config/performance.yml` schema for edge, mid-tier, and core profiles  

2. **Module Throttling & Prioritization**  
   - Integrate a throttle decorator (leveraging `offline_mode.py`) that delays lower-priority modules under load  
   - Build a priority queue so critical modules preempt less-urgent work  

3. **Parallel & Distributed Execution**  
   - Create `module_executor.py` using a thread- or process-pool for local parallelism  
   - Draft `distributed_executor.py` stub and document the inter-node protocol in `MODULE_API.md`  
   - Add integration tests simulating multi-node or concurrent execution  

## ⏳ Phase 7 – Multi-Agent Interface & Messaging

**High-Level Goals:**
- Run multiple Silhouette agents in parallel, each with its own memory store  
- Enable memory sharing, merging and persona diffing between agents  
- Provide socket- or HTTP-based inter-agent messaging  
- Add REPL commands to spawn, fork, merge, audit agents  

**Actionable Subtasks:**

1. **Agent Lifecycle & CLI Commands**  
   - Create `agent_controller.py` to manage agent processes (spawn, fork, merge, shutdown)  
   - Extend `cli/main.py` with new commands:  
     - `:agent spawn <template>`  
     - `:agent fork <agent_id>`  
     - `:agent merge <target_id> <source_id>`  
     - `:agent list`  

2. **Isolated Memory Stores & Sharing**  
   - Implement per-agent `memory_<agent_id>.jsonl` files  
   - Build `memory_merge.py` to diff & merge two agent memories  
   - Add `:agent export <agent_id> <path>` and `:agent import <agent_id> <path>`  

3. **Persona Diff & Audit**  
   - Develop `persona_diff.py` that compares `persona.dsl` across agents and highlights divergences  
   - Add `:agent audit <agent_id>` CLI to run selfcheck and persona-diff together  

4. **Inter-Agent Messaging Layer**  
   - Prototype `agent_messaging.py` using WebSockets or HTTP endpoints for agent-to-agent calls  
   - Define message formats & routes in `docs/agent_api.md`  
   - Secure communications via token or mutual TLS  

5. **Integration Tests & CI**  
   - Write pytest scenarios for:  
     - Spawning and terminating agents  
     - Forking and merging memory  
     - Exchanging messages and verifying responses  
   - Extend GitHub Actions to launch multiple agent instances in the matrix  

6. **Documentation & Examples**  
   - Create `docs/agent_scenarios.md` with end-to-end recipes (e.g., “Spawn two agents, share memory, merge results”)  
   - Update `README.md` quickstart to include multi-agent usage  

## ⏳ Phase 8 – Self-Reflective Monitoring

**High-Level Goals:**
- Detect drift in tone, intent, or behavior over time  
- Summarize what’s changed since the last session or checkpoint  
- Audit persona alignment continuously and report deviations  
- Extend the `:selfcheck` command into a full audit engine  

**Actionable Subtasks:**

1. **Drift Detection Engine**  
   - Implement `drift_detector.py` that compares recent memory entries against historical baselines  
   - Define drift metrics (e.g. topic, sentiment, intent distributions) and thresholds in `config/drift.yml`  
   - Add `:drift-report` CLI to generate a concise drift summary  

2. **Session Summarization & Trends**  
   - Build `session_summarizer.py` to produce human-readable summaries of each session  
   - Track key statistics (number of intents, tone shifts, module usage) and output to `reports/`  
   - Create `:summary` CLI to view the latest session summary or a range of sessions  

3. **Persona Audit Tool**  
   - Enhance `selfcheck_engine.py` to validate current behavior against `persona.dsl` rules  
   - Implement `persona_audit.py` to highlight any responses or memory entries that violate persona constraints  
   - Add `:persona-audit <agent_id?>` CLI to run a targeted persona audit  

4. **Extended `:selfcheck` Command**  
   - Consolidate drift reports, session summaries, and persona audits under `:selfcheck --full`  
   - Output a multi-part report with actionable warnings and remediation suggestions  

5. **Integration Tests & CI**  
   - Write pytest scenarios for drift detection using synthetic memory logs  
   - Add tests for `:drift-report`, `:summary`, and `:persona-audit` CLI commands  
   - Update CI to fail if any audit warnings exceed critical thresholds  

6. **Documentation & Examples**  
   - Document the monitoring workflow in `docs/monitoring.md`  
   - Provide example configs in `docs/examples/drift_config.yml`  
   - Update `README.md` to include “Self-Reflective Monitoring” usage guide  
