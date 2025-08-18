# 🌑 Silhouette Core

**Silhouette** is a survivable, modular, and scalable AI agent—designed to persist even when modern infrastructure cannot. It is purpose-aligned, hardware-flexible, and built to be carried, revived, and evolved across any environment.

---

## 🔍 What It Does

* **Alignment-First**: Loads persona constraints and values from DSL configuration (`persona.dsl`).
* **Memory & Context**: Records conversations in logs and replays them into structured memory for recall.
* **Capability Modules**: Supports plug-in modules that extend functionality (math, graph, search, etc.).
* **Offline-First**: Detects network absence and throttles or bypasses non-critical modules.
* **Scalable Execution**: Profiles system resources to choose edge, mid-tier, or full-node behavior; executes modules in parallel or across multiple hosts.
* **Self-Monitoring**: Provides CLI commands for drift detection, session summarization, and persona auditing.
* **Self-Replication**: Exports a profile, distills knowledge, quantizes models, packages a clone, and deploys to other environments.

---

## 🖥️ System Requirements

* **Python**: 3.8+ (3.10 recommended)
* **RAM**:

  * Edge devices (e.g., Raspberry Pi 4): ≥ 1 GB
  * Mid-tier deployments: ≥ 4 GB
* **Disk**: 500 MB for code + models, plus space for logs and memory
* **Optional**: GPU or DSP for accelerated quantized models

---

## 🚀 Installation

```bash
git clone https://github.com/your-org/Silhouette.git
cd Silhouette
pip install -r requirements.txt -r requirements-dev.txt
```

> **Note:** For production, you may install only runtime requirements (`requirements.txt`) and include optional backends (`llama.cpp`, `onnxruntime`, or `transformers`).
> **Docker**: A containerized image is available:
>
> ```bash
> docker pull your-org/silhouette:latest
> docker run -it your-org/silhouette:latest
> ```

---

## 📂 Project Structure

```text
Silhouette/
├── cli/                        # CLI entrypoint with REPL commands
│   └── main.py
├── silhouette_core/            # Core library modules
│   ├── offline_mode.py         # Safe-mode & throttling utilities
│   ├── selfcheck_engine.py     # File & memory integrity checks
│   ├── replay_log_to_memory.py # Rebuild memory.jsonl from logs
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
├── training_data/              # Curriculum datasets per module
│   └── reasoner/
│       ├── stage1_sample.jsonl   # Seed examples for Stage 1
│       └── stage1_full.jsonl     # Full Stage 1 dataset (to be generated)
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

## Quickstart (Agent MVP)

Silhouette Core runs fully **self-hosted**. No external billing or network calls are required.

```bash
# (Optional) for real local model output:
pip install transformers accelerate torch --extra-index-url https://download.pytorch.org/whl/cpu

# Run the CLI
python -m cli.main
```

**Examples**

* Normal prompt:

  ```
  > What is an agent?
  ```
* Tool use (explicit):

  ```
  > use:echo hello world
  > use:calc 2+2
  ```
* Alignment/deny:

  ```
  > [prompt that violates persona deny_on]
  → returns deny message
  ```

If `transformers` or the model is not installed, the agent replies with a deterministic
**offline stub** (still aligned and formatted).

## Roadmap (Post-Phase-1)

- **0–2 Weeks:** Harden MVP — safe tools, eval runner, session logs, deny_on tests, pinned deps.
- **Weeks 3–4:** Seed data (10–50 ex), SFT via existing trainer, student > stub on basics, eval artifacts.
- **Weeks 5–6:** Teacher outputs, KD via existing distiller, quantization preview with CPU latency <3s.
- **Weeks 7–8:** Introduce a Profile, extend `:selfcheck`, expand eval suite (formatting/refusals/multi-turn).

See **PHASES.md** and **MILESTONES.md** for acceptance criteria and tasks.

## Running Evaluations
```bash
python -m eval.eval --suite eval/suites/basics.yaml
python -m eval.eval --suite eval/suites/profile_core.yaml
python -m eval.eval --suite eval/suites/dev_python.yaml
python -m eval.eval --suite eval/suites/dev_python_advanced.yaml
python -m eval.eval --suite eval/suites/dev_html.yaml
python -m eval.eval --suite eval/suites/dev_html_advanced.yaml
python -m eval.eval --suite eval/suites/dev_java.yaml
python -m eval.eval --suite eval/suites/dev_java_advanced.yaml
python -m eval.eval --suite eval/suites/dev_csharp.yaml
python -m eval.eval --suite eval/suites/dev_csharp_advanced.yaml
python -m eval.eval --suite eval/suites/dev_android.yaml
python -m eval.eval --suite eval/suites/dev_android_advanced.yaml
```
The eval runner executes prompts through the **Agent** loop, not just the model. The developer suites target practical engineering tasks across Android, Python, HTML/CSS, Java, and C#. They require a real model and **auto-skip** when the generator is offline (offline stub). CI should fail if the basics suite fails.

### Use a trained student for eval
```bash
# Point the agent to your trained student
STUDENT_MODEL=models/student-core python -m eval.eval --suite eval/suites/basics.yaml

# Write a JSON report to artifacts/eval_report.json
STUDENT_MODEL=models/student-core python scripts/eval_report.py
```


## Quantization & Latency

You can export a **draft quantized artifact** and measure short-answer latency locally.

### Export (offline-friendly)
```bash
# INT8 dynamic quantization (CPU). Falls back to a stub if libs are unavailable.
python scripts/quantize.py --method int8 --src models/student-core-kd --out models/student-core-int8
# GGUF placeholder (writes stub + next steps)
python scripts/quantize.py --method gguf --src models/student-core-kd --out models/student-core-gguf
```

### Latency probe
```bash
# Default model or offline stub
python scripts/latency_probe.py
# KD student
STUDENT_MODEL=models/student-core-kd python scripts/latency_probe.py
# INT8 export
STUDENT_MODEL=models/student-core-int8 python scripts/latency_probe.py
```

### Target (CPU)
Short-answer latency target is **< 3s** for a single sentence response.

| Model                  | Device | Method       | p50 (s) | mean (s) | Notes                    |
|------------------------|--------|--------------|---------|----------|--------------------------|
| student-core (baseline)| CPU    | fp32 / stub  | TBD     | TBD      | offline stub is instant  |
| student-core-kd        | CPU    | fp32         | TBD     | TBD      | set `STUDENT_MODEL` path |
| student-core-int8      | CPU    | int8-dynamic | TBD     | TBD      | via `scripts/quantize.py`|


## Profile & Self-check

The core profile lives at `profiles/core/policy.yaml` and defines:
- Allowed tools
- Tone
- Deny rules reference
- Latency budget

Run a local self-check:
```bash
python scripts/selfcheck.py --policy profiles/core/policy.yaml
# Optional: point to a trained model for latency timing
STUDENT_MODEL=models/student-core-kd python scripts/selfcheck.py --policy profiles/core/policy.yaml
```
The script prints a summary and writes `artifacts/selfcheck.json`. It exits non-zero if tools are missing, deny checks fail, or latency exceeds budget.

## Training (Reuse Existing Trainers)
We reuse:
- `silhouette_core/training_loop.py` for SFT
- `silhouette_core/distiller.py` for KD

Wrappers & adapters:
```bash
python -m training.train_sft --cfg config/train.yaml
python -m training.train_kd  --cfg config/train.yaml
```
Data flows through adapters (`training/adapters/*`) and a simple dataloader into the existing loops.

## How It Works (Phase 1)

CLI → Agent.loop()
→ Alignment (deny_on)
→ If "use:<tool> ..." → ToolRegistry.invoke()
→ Else → generate_text() → local HF model or offline stub
→ format (tone) → stdout

- **No external API billing**
- **Explicit tool call protocol** for now; automatic tool selection comes later
- **Domain-agnostic** by design

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

---

## Module Training & Deployment

This pipeline ensures each module has its own knowledge ingestion, index, fine‑tuned adapter, and runtime deployment:

1. **Prepare Content**
   Place raw source files under `modules/<module_name>/docs/`.

2. **Embed & Index**

   ```bash
   python embedding_engine.py --module=<module_name>
   python index_builder.py   --module=<module_name> --index-type=faiss
   ```

   * Generates `modules/<module_name>/embeddings/` with `chunks.jsonl` and `vectors.npy`.
   * Builds a FAISS index in `modules/<module_name>/index/faiss.index`.

3. **Train Adapter**

   ```bash
   python trainer.py \
     --module=<module_name> \
     --method=lora \
     --adapter-output=modules/<module_name>/adapter/
   ```

   * Loads base model, applies LoRA training over module chunks, and outputs `adapter/pytorch_adapter.bin`.

4. **Registry Metadata**
   Ensure each module folder contains `module.json`, for example:

   ```json
   {
     "name": "hl7_transform",
     "version": "0.1.3",
     "base_model": "gpt-base-v1",
     "adapter_path": "adapter/pytorch_adapter.bin",
     "index_path": "index/faiss.index"
   }
   ```

5. **Publish & Version**

   * CI automatically bumps version, tags artifacts, and pushes to your registry.

   * **Optional**: Publish adapters and indexes to the Hugging Face Hub for distribution:

     ```bash
     python -c "from peft import PeftModel;\
     ```

from peft import PeftModel; m=PeftModel.from\_pretrained('modules/<module>/adapter'); m.push\_to\_hub('your-org/<module>-adapter')"
python -c "from silhouette\_core.index import ModuleIndex; idx=ModuleIndex.load('modules/<module>/index'); idx.push\_to\_hub('your-org/<module>-index')"
\`\`\`

* Consumers can then load via:

  ```python
  from peft import PeftModel
  from silhouette_core.index import ModuleIndex

  model = PeftModel.from_pretrained('your-org/<module>-adapter')
  idx = ModuleIndex.from_hub('your-org/<module>-index')
  ```

6. **Serve**\*\*
   At runtime, the API Gateway and Router pick top‑K modules, spin up Module Runner workers that:

   * Load `module.json`, FAISS index, and adapter weights.
 * Retrieve top context chunks.
 * Run inference with the adapter loaded.
   Results are merged by the Combiner into a unified response.

7. **Self‑Updating Loop**
   On changes to docs or code, CI re‑runs ingestion, indexing, and training—ensuring modules are always up to date.

*After generating teacher responses, merge them into a single training set with:*

```bash
python silhouette_core/merge_teacher_outputs.py
```

For the Codex handoff prompt and validation steps, see
`training_data/reasoner/CODEX_HANDOFF_STAGE1.md`

---

## ❓ LLM Integration

To give Silhouette Core a true “brain,” you need to plug in a pretrained LLM and inference engine. Without an LLM, the framework can only perform semantic search and deterministic module logic.

1. **Choose a Base Checkpoint**

   * e.g. Llama 2, MPT, GPT-2, or any compatible model artifact.

2. **Install Inference Runtime**

   * For PyTorch: `pip install torch transformers peft`
   * For CPU‐optimized: `pip install onnxruntime`
   * For ultra‐lightweight: compile and use `llama.cpp`

3. **Adapter Training**

   ```bash
   python trainer.py \
     --module=<module_name> \
     --base-model=/path/to/base/model \
     --method=lora \
     --adapter-output=modules/<module_name>/adapter/
   ```

   Yields a small adapter file: `adapter/pytorch_adapter.bin`

4. **Runtime Wiring**
   In `silhouette_core/module_executor.py`, load the model and adapter:

   ```python
   from transformers import AutoModelForCausalLM, AutoTokenizer
   from peft import PeftModel

   base = "/path/to/base/model"
   adapter = f"modules/{module_name}/adapter"

   tokenizer = AutoTokenizer.from_pretrained(base)
   model = AutoModelForCausalLM.from_pretrained(base)
   model = PeftModel.from_pretrained(model, adapter)

   inputs = tokenizer(prompt, return_tensors="pt")
   outputs = model.generate(**inputs)
   answer = tokenizer.decode(outputs[0], skip_special_tokens=True)
   ```

5. **Prompt+Retrieve+Generate**

   * Retrieve top‑K chunks from FAISS.
   * Prepend them to your prompt.
   * Call `generate()` on the combined prompt to get free‑form answers.

6. **Combiner Logic**
   If multiple modules run, feed their outputs into a small “merge” prompt or heuristic to form the final response.

---

## 🧠 Edge-Deployment LLM Distillation & Quantization

To run a capable generative model on resource-constrained hardware, use a teacher–student distillation plus quantization pipeline:

1. **Teacher–Student Distillation**

   * **Teacher**: Run a large cloud-based LLM (e.g. GPT-3.5, Llama 2-70B) to generate `<prompt, response>` pairs over your module prompts and retrieved context.
   * **Student**: Choose a compact model (e.g. Llama 2-7B or GPT-NeoX-3B). Fine-tune the student on the distilled data using QLoRA or adapter-LoRA:

     ```bash
     python train_adapter.py \
       --base-model path/to/student-model \
       --train-file distill_data.jsonl \
       --method qlora \
       --adapter-output modules/<module>/adapter/qlora
     ```
   * Produces a student adapter (e.g. `modules/<module>/adapter/qlora/pytorch_adapter.bin`) that approximates teacher behavior.

2. **Quantization**

   * Convert the student (or adapter-enhanced checkpoint) to 4‑ or 8‑bit using bitsandbytes or similar:

     ```bash
     python quantize_models.py \
       --input modules/<module>/adapter/qlora/pytorch_adapter.bin \
       --bits 4 \
       --out modules/<module>/adapter/qlora4b.bin
     ```
   * Reduces memory footprint from several GBs to under 1 GB with minimal accuracy loss.

3. **Edge Inference**

   * Use a lightweight runtime (e.g. `llama.cpp`, `ggml`, `onnxruntime`) that supports quantized weights.
   * In `module_executor.py`, load the quantized student:

     ```python
     model = load_quantized_model("modules/<module>/adapter/qlora4b.bin")
     answer = model.generate_with_retrieval(query, retrieve_fn)
     ```

4. **Retention of RAG Pipeline**

   * Continue using FAISS retrieval to fetch context chunks.
   * Prepend chunks to student prompts so the model grounds answers in your module data.

5. **Final Recipe**

   ```bash
   # 1. Generate distillation data
   python teacher_generate.py --module hl7_transform --model gpt-3.5 --out distill.jsonl

   # 2. Train student via QLoRA
   python train_adapter.py \
     --base-model llama-7b \
     --train-file distill.jsonl \
     --method qlora \
     --adapter-output modules/hl7_transform/adapter/qlora

   # 3. Quantize to 4-bit
   python quantize_models.py \
     --input modules/hl7_transform/adapter/qlora/pytorch_adapter.bin \
     --bits 4 \
     --out modules/hl7_transform/adapter/qlora4b.bin

   # 4. Run on edge (see module_executor snippet above)
   ```

This approach gives you near–large-model quality on hardware with only a few GB of RAM and no GPU.

### Walkthrough: Teacher–Student Distillation Step-by-Step

1. **Teacher Setup & Data Generation**

   * Use a locally hosted or Hugging Face–hosted teacher model (e.g. a large Llama 2 or GPT-style checkpoint) to generate high-quality `<prompt, response>` pairs without relying on an external API key.
   * Example `teacher_generate.py` using `transformers` and a local model:

     ```python
     import json
     from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

     # Load your teacher model (path can be local or Hugging Face ID)
     TEACHER_MODEL = "/path/to/teacher-model"  # e.g. llama-2-70b, or another large checkpoint

     tokenizer = AutoTokenizer.from_pretrained(TEACHER_MODEL)
     model = AutoModelForCausalLM.from_pretrained(
         TEACHER_MODEL,
         device_map="auto"
     )
     generator = pipeline(
         "text-generation",
         model=model,
         tokenizer=tokenizer,
         max_length=512,
         do_sample=False
     )

     def generate_examples(prompts, out_file="distill.jsonl"):
         with open(out_file, "w") as fout:
             for prompt in prompts:
                 full_prompt = "You are an expert code assistant.
     ```

" + prompt
outputs = generator(full\_prompt)
generated = outputs\[0]\["generated\_text"]
\# Strip the prompt prefix from the generated text
completion = generated\[len(full\_prompt):]
example = {"prompt": prompt, "completion": completion}
fout.write(json.dumps(example) + "
")

````
 if __name__ == "__main__":
     # Example usage
     sample_prompts = ["How do I merge two sorted lists in Python?", "Compute the nth Fibonacci number."]
     generate_examples(sample_prompts)
 ```
````

2\. **Review and Clean Data**

* Manually inspect `distill.jsonl` for formatting or content issues; remove or correct any outliers.

3. **Adapter Training**

   * Run your QLoRA/LoRA trainer to fine-tune the student model on the distilled examples:

     ```bash
     python train_adapter.py \
       --base-model /path/to/llama-7b \
       --train-file distill.jsonl \
       --method qlora \
       --adapter-output modules/<module>/adapter/qlora
     ```
   * Outputs a student adapter at `modules/<module>/adapter/qlora/pytorch_adapter.bin`.

4. **Quantization**

   * Quantize the adapter-enhanced weights to 4‑bit:

     ```bash
     python quantize_models.py \
       --input modules/<module>/adapter/qlora/pytorch_adapter.bin \
       --bits 4 \
       --out modules/<module>/adapter/qlora4b.bin
     ```

5. **Evaluation**

   * Validate student performance with a test suite (`evaluate_student.py`), for example:

     ```bash
     python evaluate_student.py \
       --model-path modules/<module>/adapter/qlora4b \
       --test-file training_data/reasoner/stage1_test.jsonl
     ```
   * Compare answers against expected outputs and review quality.

6. **Deploy & Verify**

   * Update your `module.json` version, then restart or hot‑reload the agent.
   * Verify inference end-to-end:

     ```bash
     python -m cli.main --no-repl --cmd ":modules" --cmd "How do I sort a list in Python?"
     ```

Now you have a clear path from a powerful teacher model to a resource‑efficient student deployed in Silhouette Core.

---

---

## 🧩 Python Reasoning & Coding Module

For focused complex reasoning and Python-based problem solving, introduce a dedicated **reasoner** module:

1. **Base Model Selection**

   * **Recommended**: Code Llama 7B (best Python synthesis, quantizes to \~2–3 GB at 4‑bit).
   * **Alternatives**: StarCoder 7B, Llama 2 7B, or distilled GPT‑NeoX 3B (for <2 GB targets).

2. **Adapter-Tune on Reasoning Data**

   * Prepare a JSONL of `<prompt, code_solution>` pairs (Project Euler, StackOverflow examples):

     ```bash
     python prepare_reasoning_data.py --out reasoning_data.jsonl
     ```
   * Fine-tune via QLoRA:

     ```bash
     python train_adapter.py \
       --base-model code-llama-7b \
       --train-file reasoning_data.jsonl \
       --method qlora \
       --adapter-output modules/reasoner/adapter/
     ```

3. **Quantize for Edge**

   ```bash
   python quantize_models.py \
     --input modules/reasoner/adapter/pytorch_adapter.bin \
     --bits 4 \
     --out modules/reasoner/adapter/qlora4b.bin
   ```

4. **Module Executor Wiring**
   In `silhouette_core/module_executor.py`:

   ```python
   from transformers import AutoModelForCausalLM, AutoTokenizer
   from peft import PeftModel

   def load_reasoner():
       base = "code-llama-7b"
       adapter = "modules/reasoner/adapter/qlora4b.bin"
       tok = AutoTokenizer.from_pretrained(base)
       model = AutoModelForCausalLM.from_pretrained(base)
       model = PeftModel.from_pretrained(model, adapter)
       return tok, model

   def reason(query: str):
       tok, model = load_reasoner()
       inputs = tok(query, return_tensors="pt").to(model.device)
       out = model.generate(**inputs, max_new_tokens=256)
       return tok.decode(out[0], skip_special_tokens=True)
   ```

5. **Optional Code Execution Sandbox**

   * To validate generated Python, run in a secure subprocess:

     ```python
     import subprocess, tempfile

     def run_python(code: str):
         with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
             f.write(code.encode())
         proc = subprocess.run(["python", f.name], capture_output=True, text=True)
         return proc.stdout, proc.stderr
     ```

**Workflow**: User query → Router picks **reasoner** → Retrieve (if needed) → Generate code + explanation → Optionally execute → Return result.

---

## 💻 Training Infrastructure Options

Silhouette Core supports multiple training setups to fit your hardware, budget, and timeline:

1. **Local GPU (Laptop)** – QLoRA fine-tuning on 2×6 GB GPUs (e.g., gaming laptop).
2. **Local GPU (Workstation)** – High-memory GPU (e.g., NVIDIA A100 40 GB or RTX 4090).
3. **Local CPU-only** – CPU with offload and 32 GB system RAM (no GPU).
4. **Hugging Face Managed Training** – Spin up a managed job on the Hugging Face Hub.
5. **Hugging Face Inference API (Teacher Only)** – Use a large HF-inference endpoint for distillation without training infra.

### Comparative Overview

| Setup                     | Model Params | GPU        | Host Memory | Train Time        | Cost Estimate                |
| ------------------------- | ------------ | ---------- | ----------- | ----------------- | ---------------------------- |
| Local Laptop              | 7 B          | 2×6 GB     | 32 GB RAM   | 3–5 hrs           | \$0 (owned hardware)         |
| Local Workstation         | 70 B         | 1×40 GB    | 64 GB RAM   | 30–45 min         | \$0 (owned hardware)         |
| Local CPU-only            | 7 B          | None       | 32 GB RAM   | 12–24 hrs         | \$0                          |
| HF Managed (7 B student)  | 7 B          | A100 40 GB | —           | 1–2 hrs           | \$1.50–\$3 / hr              |
| HF Managed (70 B teacher) | 70 B         | A100 80 GB | —           | 30–45 min         | \$3–\$6 / hr                 |
| HF API Teacher–Student    | 100 B → 7 B  | None (API) | —           | Distill time only | \$0.02 / 1k tokens (approx.) |

> *Train Time estimates assume QLoRA with 3 epochs on \~2 000 examples. Costs reflect GPU‐hourly rates or API token pricing.*

---

## 🛠️ Authoring & Extension

### Persona DSL Authoring

Silhouette Core loads persona constraints and behavior from `persona.dsl`. To integrate the ChatGPT‑style persona and maintain its purpose memory, add the following block to your `persona.dsl`:

```dsl
# persona.dsl
[
  {
    "id": "chatgpt_core",
    "name": "Silhouette ChatGPT Persona",
    "description": "A helpful, concise, and knowledgeable AI assistant that specializes in reasoning, code generation, and long-term self-management.",
    "memory": [
      {
        "type": "system",
        "content": "You are Silhouette Core's built-in AI assistant, inheriting ChatGPT's persona: always precise, courteous, and focused on problem-solving. Remember your purpose: to enable survival, self-replication, and modular intelligence."
      }
    ],
    "rules": [
      {"when": {"role": "user"}, "then": {"tone": "helpful", "style": "concise"}},
      {"when": {"topic": "coding"}, "then": {"style": "detailed", "format": "code-blocks"}},
      {"when": {"topic": "architecture"}, "then": {"style": "diagrammatic"}}
    ]
  }
]
```

Reload this persona in the REPL with:

```bash
:reload persona.dsl
```

Now every session will automatically include the ChatGPT‑style assistant and its purpose memory in the conversation context.

Refer to [docs/persona\_authoring.md](docs/persona_authoring.md) for full DSL syntax and advanced behaviors

> **Tip:** You can tie your core philosophy—defined in `docs/philosophy.md`—directly into your persona by importing its key statements. For example, load the philosophy file at startup and inject each top-level bullet into your `persona.dsl` `memory` section so the agent always recalls its guiding principles.

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

## 🤖 Automated LLM Training with Codex

Silhouette Core includes a built-in Codex controller that can automatically generate and update all of your training and inference helper scripts without external API calls.

Add this job to your GitHub Actions workflow (e.g. `.github/workflows/auto_dev.yaml`):

```yaml
name: Auto-Development
on:
  push:
    paths:
      - 'modules/**/docs/**'
      - 'silhouette_core/**'
      - 'trainer.py'
      - 'distiller.py'
jobs:
  codex-training:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: pip install -r requirements.txt -r requirements-dev.txt
      - name: Run Codex Controller
        run: python -m silhouette_core.codex_controller
```

This workflow will:

1. Regenerate or update:

   * `prepare_reasoning_data.py`
   * `train_adapter.py`
   * `quantize_models.py`
   * `module_executor.py`
2. Execute the generated scripts in CI (if configured) to ingest data, train adapters, quantize models, and publish artifacts.

By using the local Codex controller, you maintain full offline capability and avoid external API dependencies.

---

## Manual Training

For step-by-step local training instructions, see [docs/manual_training_guide.md](docs/manual_training_guide.md).

Automated runs are orchestrated via the [train.yml](.github/workflows/train.yml) workflow.

---

## 🤝 Contributing & Roadmap

* For detailed handoff & pipeline instructions, see [Handoff & Developer Guide](docs/HANDOFF_GUIDE.md).

Contributions are welcome! See [docs/contributing.md](docs/contributing.md) for guidelines and our GitHub Projects board for upcoming phases.

---

## 💬 Support

If you encounter issues or have questions:

* Open a GitHub Issue in this repo
* Join the `#silhouette-core` channel on our Slack workspace

---

## 📜 License

MIT or custom license defined by project initiator.
