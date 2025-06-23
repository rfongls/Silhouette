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
- Profiles for edge, mid-tier, and high-capacity deployments
- Throttle and prioritize modules based on system load
- Enable parallel or distributed module execution

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
