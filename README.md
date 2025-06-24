````markdown
# 🌑 Silhouette Core

**Silhouette** is a survivable, modular, and scalable AI agent—designed to persist even when modern infrastructure cannot. It is purpose-aligned, hardware-flexible, and built to be carried, revived, and evolved across any environment.

---

## 🔍 What It Does

- **Alignment-First**: Loads persona constraints and values from DSL configuration (`persona.dsl`).  
- **Memory & Context**: Records conversations in logs and replays them into structured memory for recall.  
- **Capability Modules**: Supports plug-in modules that extend functionality (math, graph, search, etc.).  
- **Offline-First**: Detects network absence and throttles or bypasses non-critical modules.  
- **Scalable Execution**: Profiles system resources to choose edge, mid-tier, or full-node behavior; executes modules in parallel or across multiple hosts.  
- **Self-Monitoring**: Provides CLI commands for drift detection, session summarization, and persona auditing.  
- **Self-Replication**: Exports a profile, distills knowledge, quantizes models, packages a clone, and deploys to other environments.

---

## 🖥️ System Requirements

- **Python**: 3.8+ (3.10 recommended)  
- **RAM**:  
  - Edge devices (e.g., Raspberry Pi 4): ≥ 1 GB  
  - Mid-tier deployments: ≥ 4 GB  
- **Disk**: 500 MB for code + models, plus space for logs and memory  
- **Optional**: GPU or DSP for accelerated quantized models  

---

## 🚀 Installation

```bash
git clone https://github.com/your-org/Silhouette.git
cd Silhouette
pip install -r requirements-dev.txt
````

> **Note:** For production, you may install only runtime requirements (`requirements.txt`) and include optional backends (`llama.cpp`, `onnxruntime`, or `transformers`).
> **Docker**: A containerized image is available:
>
> ```bash
> docker pull your-org/silhouette:latest
> docker run -it your-org/silhouette:latest
> ```

---

## 📂 Project Structure

```
Silhouette/
├── cli/                        # CLI entrypoint with REPL commands
│   └── main.py
├── silhouette_core/            # Core library modules
│   ├── offline_mode.py         # Safe-mode & throttling utilities
│   ├── selfcheck_engine.py     # File & memory integrity checks
│   ├── replay_log_to_memory.py # Rebuild memory.jsonl from logs
│   ├── performance_profiler.py # Resource usage measurement
│   ├── module_executor.py      # Local parallel executor
│   ├── distributed_executor.py # Stub for multi-node execution
│   ├── agent_controller.py     # Spawn/fork/merge agents
│   ├── agent_messaging.py      # Inter-agent communication
│   ├── memory_merge.py         # Merge or diff agent memories
│   ├── persona_diff.py         # Compare persona DSL across agents
│   ├── drift_detector.py       # Tone/intent drift analysis
│   ├── session_summarizer.py   # Human-readable session summaries
│   ├── persona_audit.py        # Persona compliance checks
│   ├── profile_exporter.py     # Export persona/memory/modules profile
│   ├── distiller.py            # Knowledge distillation & compression
│   ├── quantize_models.py      # Embedding/model quantization
│   └── package_clone.py        # Build a deployable clone archive
├── config/                     # Config schemas for performance, drift, distillation
│   ├── performance.yml
│   ├── drift.yml
│   └── distillation.yml
├── docs/                       # Markdown guides and examples
│   ├── monitoring.md
│   ├── self_replication.md
│   ├── deploy-guide.md
│   ├── agent_api.md
│   ├── agent_scenarios.md
│   └── examples/
│       ├── drift_config.yml
│       └── distillation_config.yml
├── tests/                      # Unit & integration tests
├── export.py                   # Encrypted backup script
├── restore.py                  # Encrypted restore script
├── CHANGELOG.md
├── ACCOMPLISHMENTS.md
├── PHASES.md
├── MILESTONES.md
└── README.md                   # This file
```

---

## ⚙️ Usage Guide

### CLI Quickstart

```bash
python -m cli.main
```

**Key commands** (type `:help` in the REPL for full list):

| Command                   | Description                                              |
| ------------------------- | -------------------------------------------------------- |
| `:reload`                 | Reload DSL and modules                                   |
| `:modules`                | List available capability modules                        |
| `:replay`                 | Replay session logs into `memory.jsonl`                  |
| `:selfcheck`              | Check file and memory integrity                          |
| `:selfcheck --full`       | Full audit: drift, summary, persona compliance           |
| `:export-profile`         | Export persona, memory, and module profile (JSON or ZIP) |
| `:distill`                | Run knowledge distillation pipeline                      |
| `:drift-report`           | Report drift in tone or intent                           |
| `:summary`                | Summarize latest session                                 |
| `:persona-audit`          | Audit memory entries against persona rules               |
| `:backup`                 | Create encrypted backup archive                          |
| `:agent spawn <template>` | Spawn a new agent from template                          |
| `:agent fork <id>`        | Fork an existing agent’s memory                          |
| `:agent merge <a> <b>`    | Merge two agents’ memories                               |
| `:agent list`             | List running agents                                      |
| `:agent deploy <target>`  | Deploy a clone archive to `<target>` (local or SSH)      |
| `:exit` / `:quit`         | Exit the REPL                                            |

*Full command reference is available in* [CLI Reference](docs/cli_reference.md).

---

## 📦 Package & Deploy Clone (Self-Replication)

```bash
# 1. Export current agent profile
python -m silhouette_core.profile_exporter --out silhouette_profile.json

# 2. Distill knowledge for edge
python -m silhouette_core.distiller --profile silhouette_profile.json

# 3. Quantize embeddings/models
python -m silhouette_core.quantize_models --input distillate.json

# 4. Package clone archive
python -m silhouette_core.package_clone --profile silhouette_profile.json --distill distillate.json --out silhouette_clone_v1.zip

# 5. Deploy to another host or device
python -m agent_controller deploy user@remote:/path

# 6. On target, run edge launcher
python -m silhouette_core.edge_launcher --profile silhouette_profile.json
```

### Troubleshooting Common Issues

* **Profile Export Fails**: Ensure `persona.dsl` and `memory.jsonl` exist and are readable.
* **Distillation Errors**: Verify `config/distillation.yml` parameters (summary length, quantization levels).
* **Quantization Failures**: Install required libs (`onnxruntime`, `tflite-runtime`) and compatible hardware.
* **SSH Deploy Issues**: Confirm SSH keys are configured and target host is reachable.

For full details, see [Self-Replication Guide](docs/self_replication.md) and [Deploy Guide](docs/deploy-guide.md).

---

## 👩‍💻 Developer & Training Workflow

Silhouette provides a pipeline for ingestion, retraining, and continuous evolution:

1. **Log Generation & Replay**

   ```bash
   python -m cli.main --no-repl --cmd :replay
   ```

2. **Knowledge Ingestion & Embedding**

   ```bash
   python -m silhouette_core.trainer \
     --source docs/knowledge_store/ \
     --memory memory.jsonl \
     --out knowledge_corpus.jsonl
   python -m silhouette_core.embedding_engine \
     --build-index \
     --input knowledge_corpus.jsonl
   ```

3. **Auto-Development Loop**

   ```bash
   python -m silhouette_core.codex_controller run
   ```

   * Define Codex steps in `auto_dev.yaml`, review generated code, then commit.

4. **Continuous Integration**
   Configure GitHub Actions to replay logs, retrain embeddings, lint, test, and regenerate docs in one pipeline.

5. **Scheduled Retraining**
   Use GitHub Scheduled Workflows or a CRON job to run the above steps nightly or weekly.

---

## 🛠️ Authoring & Extension

### Persona DSL Authoring

* Write or update alignment rules in `persona.dsl`.
* Refer to [docs/persona\_authoring.md](docs/persona_authoring.md) for syntax and examples.

### Performance Profiles

* Edit `config/performance.yml` to define new profiles:

  * **edge**: minimal modules, aggressive throttling
  * **mid-tier**: balanced CPU/memory usage
  * **core**: full-module parallel execution

### Environment Variables

* `SILHOUETTE_OFFLINE=1` — Force safe/offline mode
* `SILHOUETTE_LOG_DIR` — Custom log directory (default `logs/`)
* `SILHOUETTE_PROFILE` — Default profile for `edge_launcher.py`

---

## 🤝 Contributing & Roadmap

Contributions are welcome! See [docs/contributing.md](docs/contributing.md) for guidelines and our GitHub Projects board for upcoming phases.

## 💬 Support

If you encounter issues or have questions:

* Open a GitHub Issue in this repo
* Join the `#silhouette-core` channel on our Slack workspace

---

## 📜 License

MIT or custom license defined by project initiator.

```
```
