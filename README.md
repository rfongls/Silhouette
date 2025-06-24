# 🌑 Silhouette Core
[![Coverage](https://codecov.io/gh/your-org/Silhouette/branch/main/graph/badge.svg)](https://codecov.io/gh/your-org/Silhouette)

**Silhouette** is a survivable, modular, and scalable AI agent—designed to persist even when modern infrastructure cannot. It is purpose-aligned, hardware-flexible, and built to be carried, revived, and evolved across any environment.

## 🔍 Overview

Silhouette Core is a foundational package for running lightweight, alignment-preserving language model agents. It focuses on:
- **Minimal runtime capability**
- **Offline survivability**
- **Expandable modules for capability growth**
- **Values-based reasoning even without cloud access**

## 🚀 Quickstart

1. Clone this repo
2. Install dependencies via `llama.cpp` or local Python-based backends
3. Load alignment capsule
4. Begin interaction using CLI or Web UI
5. Optionally spawn additional agents with `agent_controller.spawn_agent()`

## 📦 Structure

```
/silhouette_core    - Core runtime modules
/docs               - Documentation and DSL alignment files
/models             - Local or referenced model binaries
/modules            - Drop-in capability modules
```

## 🛠 Requirements

- CPU-compatible LLM (1–2B parameters)
- Python 3.8+
- `llama.cpp` or `onnxruntime` or `transformers` (optional)

## 📜 License

MIT or custom license to be defined by project initiator.

## 🧭 Self-Reflective Monitoring

Run monitoring tools via the CLI:
- `:drift-report` to check tone drift
- `:summary` to summarize the latest session
- `:persona-audit` to verify persona adherence
- `:selfcheck --full` for the complete audit
- `:export-profile` to bundle persona, memory, and modules

