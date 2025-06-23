# 🧠 Silhouette Core – SYSTEM_OVERVIEW.md

## 📦 Project Purpose

Silhouette Core is a modular, memory-persistent AI runtime capable of:
- CLI and API interactions
- Intent, tone, and persona parsing
- Graph-based memory context linking
- Semantic search and self-recovery
- Autonomous development cycles via Codex

It is designed to be resilient, portable, and able to rebuild itself from logs and modules alone.

---

## 🧭 System Architecture

```
           +--------------------+
           |  CLI (main.py)     | <--------+
           +--------------------+          |
                     |                     |
       +-------------v------------+        |
       | response_engine.py       |        |
       | alignment_engine.py      |        |
       +-------------+------------+        |
                     |                     |
     +--------+------+--------+            |
     |   Intent  |   Tone     |            |
     | Engine    |  Parser    |            |
     +-----------+------------+            |
                     |                     |
             +-------v---------+           |
             | Memory Core     |           |
             | Graph Engine    |           |
             +-----------------+           |
                     |                     |
              +------v------+              |
              |  API Server  |-------------+
              | FastAPI      |
              +-------------+
```

---

## 🔗 Runtime Flow

1. **User Input** → CLI or API
2. Input is parsed for `intent`, `tone`, `alignment` checks
3. Response is generated or denied, based on DSL config
4. Logs and memory are updated
5. Optional: Graph is built, search is performed, modules are run

---

## 📚 File Index & Purpose

| File | Purpose |
|------|---------|
| `cli/main.py` | Entry point CLI REPL |
| `cli/response_engine.py` | Applies persona and formats response |
| `alignment_engine.py` | Loads and enforces persona rules |
| `intent_engine.py` | Maps phrases to semantic intents |
| `tone_parser.py` | Detects tone (happy, confused, etc.) |
| `memory_core.py` | Reads/writes from `memory.jsonl` |
| `graph_engine.py` | Links memory entries into a graph |
| `embedding_engine.py` | Performs semantic search with TF-IDF |
| `interface_server.py` | FastAPI endpoints for all major features |
| `export.py` / `restore.py` | Encrypted backup/restore logic |
| `trainer.py` | Ingests knowledge into memory from markdown |
| `module_loader.py` | Dynamically loads plug-in modules |
| `docs/alignment_kernel/persona.dsl` | DSL config for tone and deny-lists |
| `logs/` | All logs and memory entries are stored here |
| `tests/` | Validates each system module with Pytest |

---

## 🔄 Rebuild Procedure (From Backup or Logs Only)

1. **Restore backup**:  
   ```bash
   python -m silhouette_core.restore --zip backup.zip --key keyfile.key
   ```

2. **Or manually rebuild:**
   - Recreate folders: `logs/`, `modules/`, `docs/alignment_kernel/`
   - Recover DSL: `persona.dsl`, `values.dsl`
   - Restore `memory.jsonl` from `logs/` or regenerate from transcripts
   - Reinstall requirements
   - Run CLI:
     ```bash
     python cli/main.py
     ```

---

## ⚠️ Fallback Strategy

| Component | Recovery Source |
|----------|------------------|
| Memory   | `logs/memory.jsonl` or logs/session_*.txt |
| Modules  | `modules/*.py/json` |
| Persona  | `docs/alignment_kernel/persona.dsl` |
| Alignment DSL | `values.dsl` |
| Core Logic | All logic files are in `silhouette_core/` and reloadable |
| Codex Dev State | `auto_dev.yaml`, `silhouette_core/codex_controller.py`, `PROJECT_MANIFEST.json` |

---

This document ensures any future contributor—or even Codex—can reconstruct and operate Silhouette Core with or without access to this system.
