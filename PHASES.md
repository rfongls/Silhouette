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

## ⏳ Phase 3 – Interoperable Context Engine
- Link memory entries to form a conversation graph
- Memory embeddings (or lightweight approximation)
- Session summarization & lookup

## ⏳ Phase 4 – Persona, Alignment, and Ethical Guardrails
- DSL-defined behavior/personality profiles
- Tone adjustment modules (e.g. sarcastic, helpful)
- Alignment boundaries in configuration

## ⏳ Phase 5 – Offline-First + Recovery
- Fallback to logs and static config when memory/core fails
- Stateless mode w/ auto-generated recovery prompts
- Tools to regenerate modules/docs from prior usage

## ⏳ Phase 6 – Scaling from Edge to Core
- Load throttling and modular resource prioritization
- Profiles for low/mid/high tier hardware:
  - Raspberry Pi, Docker container, high-memory VM
- Distributed processing support
