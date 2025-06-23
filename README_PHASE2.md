# Silhouette Core – Phase 2 Overview

Phase 2 builds the brain and memory around the existing runtime CLI.

🔧 **Key Systems:**
- `intent_engine.py` — Maps user input to semantic intent
- `memory_core.py` — Stores/retrieves embeddings from session logs
- `tone_parser.py` — Scores emotional tone
- `interface_server.py` — Provides optional GUI or API access

💡 **Strategy:**
Every interaction is logged and codified. Each session can be rebuilt from logs and DSL configs. No dependency on upstream storage. Codex can rehydrate logic from logs and definitions alone.
