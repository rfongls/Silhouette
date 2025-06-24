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
- Run multiple Silhouette agents with unique memory  
- Memory sharing and persona diffing  
- Socket- or API-based inter-agent messaging  
- Commands to spawn/fork/merge agents  

## ⏳ Phase 8 – Self-Reflective Monitoring
- Detect drift in tone, intent, or behavior  
- Summarize changes since last session  
- Audit persona alignment  
- Introduce `:selfcheck` command and audit engine  