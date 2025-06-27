# Codex Module Training Handoff

This document explains everything you need to add the new **Codex** (Coding & Advanced Reasoning) module into our Silhouette training pipeline, from data preparation through Hugging Face–driven fine-tuning, up to deployment in our framework.

---

## 1. Overview

- **Module name:** `codex`  
- **Purpose:** Fine-tune a large LLM (CodeLlama-70B-Instruct) with LoRA adapters to specialize in multi-language coding (Python, Java, C#, HTML/JS etc.) and advanced chain-of-thought reasoning, then distill/quantize for on-device inference.  
- **Outputs:**  
  - LoRA adapter checkpoint artifacts under `modules/codex/adapter/`  
  - Optional HF Hub repo `silhouettellc/silhouette-codex` with every checkpoint versioned  

---

## 2. Prerequisites

- **Python** ≥ 3.10  
- **CUDA** drivers if training locally (11.7+) or GPU-enabled Space  
- **Hugging Face CLI** & **Accelerate**  
  ```bash
  pip install transformers accelerate bitsandbytes peft huggingface_hub
  huggingface-cli login   # use Silhouette-Core-Training token
  accelerate config        # set up for 4 GPU / fp16
````

* **Git** permissions on `rfongls/Silhouette` and HF org `silhouettellc`

---

## 3. Directory Structure

```
.
├── modules/
│   └── codex/
│       ├── data/
│       │   ├── train.jsonl
│       │   └── valid.jsonl
│       └── adapter/               # LoRA outputs
├── training/
│   ├── configs/
│   │   └── codex.json             # new config
│   └── train.py                   # existing training script
├── Dockerfile                     # for HF Space / containerized runs
├── accelerate_config.yaml         # (optional) accelerate defaults
└── docs/
    └── codex_handoff.md           # this document
```

---

## 4. Data Preparation

1. **Collect prompt–completion pairs** covering:

   * Language syntax & APIs (Python, Java, C#, JS/HTML)
   * “HumanEval”-style coding tests
   * StackOverflow Q&A
   * Chain-of-thought puzzles (GSM-8K examples)
2. **Format** each line as JSON:

   ````jsonl
   {"prompt":"```python\n# your code prompt…","completion":"    # expected completion…\n```"}
   ````
3. **Save** into:

   * `modules/codex/data/train.jsonl`
   * `modules/codex/data/valid.jsonl` (5–10% hold-out)
4. For seed prompts and expansion instructions, see
   `training_data/reasoner/CODEX_HANDOFF_STAGE1.md`

---

## 5. Training Configuration

Create `training/configs/codex.json`:

```jsonc
{
  "model_name_or_path":           "bigcode/codellama-70b-instruct",
  "train_file":                   "modules/codex/data/train.jsonl",
  "validation_file":              "modules/codex/data/valid.jsonl",
  "output_dir":                   "modules/codex/adapter/",
  "push_to_hub":                  true,
  "hub_repo_id":                  "silhouettellc/silhouette-codex",
  "hub_token":                    "__token__",
  "per_device_train_batch_size":  4,
  "gradient_accumulation_steps":  2,
  "per_device_eval_batch_size":   4,
  "num_train_epochs":             3,
  "learning_rate":                1e-4,
  "precision":                    "fp16",
  "logging_dir":                  "training/logs/codex"
}
```

---

## 6. Dockerfile & Accelerate Defaults

**Dockerfile** (repo root):

```dockerfile
FROM ghcr.io/huggingface/transformers-pytorch-gpu:latest

COPY . /workspace
WORKDIR /workspace

RUN pip install --no-cache-dir -r requirements-dev.txt \
    && pip install accelerate bitsandbytes peft

# (Optional) bake in accelerate config
COPY accelerate_config.yaml /workspace/

CMD accelerate launch training/train.py \
    --config training/configs/codex.json
```

**accelerate_config.yaml** (optional):

```yaml
compute_environment: MULTI_GPU
distributed_type: MULTI_GPU
num_processes: 4
mixed_precision: fp16
```

---

## 7. Hugging Face Hub Setup

1. **Create model repo**

   ```bash
   huggingface-cli repo create silhouettellc/silhouette-codex --type model
   ```
2. **Store token** as a secret `HF_TOKEN` in your HF Space or CI environment.
3. **Verify** read/write scopes for org repos and public LLM indexing.

---

## 8. Running Training

### Locally

```bash
export HF_TOKEN=<your_token>
accelerate launch training/train.py \
  --config training/configs/codex.json
```

### In a Hugging Face Space

* **New Space** (Docker + GPU → 4×L4) pointing at this repo
* Add `HF_TOKEN` secret
* Build & watch Logs; containers runs `CMD` fine-tuning automatically

---

## 9. Post-Training & Integration

* **Checkpoint artifacts** in `modules/codex/adapter/`
* **Adapters on HF Hub** under `silhouettellc/silhouette-codex`
* **Inference integration**: in your `cli/main.py` & `module_loader.py`, register:

  ```python
  {
    "name": "codex",
    "model_name_or_path": "modules/codex/adapter/",
    "type": "code-generation"
  }
  ```
* **Quantize or distill** as needed (use `silhouette_core/quantize_models.py`)

---

## 10. Next Steps & PR Workflow

1. **Branch:** `staging/codex-handoff`
2. **Include:**

   * `docs/codex_handoff.md`
   * `training/configs/codex.json`
   * `Dockerfile` & `accelerate_config.yaml`
3. **Open PR → CI → Review → Merge to `main`**
4. **Trigger** Space build or local run

---

With this in place, the Codex module can be trained, versioned, and deployed end-to-end using your existing Silhouette framework and Hugging Face GPU resources. Let me know if you need any templates or examples for the training script itself!
