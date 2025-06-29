# Module Training Guides

Below are the fine-tuning workflows, data sources, model choices, and deployment considerations for each Silhouette Core module. Place this under `docs/Module Guides/`.

---

## 1. Coding & Advanced Reasoning Module

**Objective:** a Python-focused “coding assistant” that can expand into Java, C#, Android, HTML/JS, etc., and run on machines with limited RAM/CPU.

| Step                   | Details                                                                                                 |
|------------------------|---------------------------------------------------------------------------------------------------------|
| **Base model**         | Start from a mid-sized open checkpoint (e.g. GPT-NeoX-20B or LLaMA-7B) that balances capacity & footprint. |
| **Data sources**       | - CodeParrot / CodeSearchNet (Python, Java, C# samples)<br>- “HumanEval” style code+test pairs<br>- StackOverflow Q&A dumps (filtered per-language) |
| **Fine-tuning method** | 1. PEFT with LoRA adapters (rank = 8–16) to minimize GPU/RAM usage<br>2. Chain-of-thought exemplars for reasoning puzzles (GSM-8K) |
| **Hyperparams**        | LR = 1e-4, batch = 8–16, epochs = 3–5; enable gradient checkpointing                                    |
| **Quantization**       | Post-train INT8 quantization (bitsandbytes) for inference                                               |
| **Artifact**           | `models/coding-python-lora/` plus per-language adapters (e.g. `coding-java.lora`, etc.)                  |
| **Inference**          | Load base + language adapter; on constrained devices, load the INT8-quantized model with `device_map="auto"` |

---

## 2. General Chat & Reasoning Module

**Objective:** handle open-domain Q&A (science, math, survival reasoning), with strong chain-of-thought capability.

| Step                   | Details                                                                                       |
|------------------------|-----------------------------------------------------------------------------------------------|
| **Base model**         | LLaMA-13B or Falcon-7B (trade off reasoning vs. footprint)                                    |
| **Data sources**       | - OpenAssistant / Alpaca-style dialogue pairs<br>- GSM-8K & MATH (math reasoning)<br>- ARC (science QA) |
| **Fine-tuning method** | 1. Supervised fine-tuning on QA pairs<br>2. CoT prompting with step-by-step solutions<br>3. Optional RLHF pass for polish |
| **Hyperparams**        | LR = 3e-5, batch = 4, epochs = 4; `warmup_steps` = 500                                        |
| **Quantization**       | INT8 or FP16 with dynamic quantization                                                        |
| **Artifact**           | `models/general-chat/`                                                                        |
| **Inference**          | Standard HF pipeline; optional distillation into a 4–5 B model for very constrained devices   |

---

## 3. Survival Knowledge Base (Tiny)

**Objective:** a highly distilled, small-footprint (~1–3 B) model to answer “how to make fire,” “improvise medicine,” etc., on phones or Pi devices.

| Step                   | Details                                                                                                                                                                                        |
|------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Base model**         | A 3 B-parameter distilled model (e.g. distilled-LLaMA or Vicuna-3B)                                                                                                                             |
| **Data sources**       | - WikiHow survival articles<br>- REI / Boy Scouts survival guides<br>- First-aid manuals (public domain)<br>- Ethnobotany & traditional medicine databases (USDA, Native American)<br>- Herbal & folk remedy monographs<br>- Gunpowder/black powder recipes & basic chemistry texts<br>- DIY water filtration & purification guides (WHO/EPA, biosand, ceramic filters)<br>- Solar energy & battery construction tutorials (Instructables, Cornell)<br>- Improvised medicine & tool-making guides (e.g. “Improvised Medicine”)<br>- Community-sourced tips (forums, Reddit) |
| **Fine-tuning method** | LoRA (rank = 4) + knowledge distillation from the full-sized general-chat module                                                                                                                |
| **Hyperparams**        | LR = 5e-5, batch = 8, epochs = 2                                                                                                                                                                |
| **Quantization**       | INT8 quant; optionally prune 10–20 % of weights                                                                                                                                                 |
| **Artifact**           | `models/survival-tiny/`                                                                                                                                                                        |
| **Inference**          | Load on Pi/phone with `device_map="cpu"` and low-res generation settings (`max_new_tokens=64`)                                                                                                   |

---

## 4. Healthcare Bot (HL7 & Clinical)

**Objective:** deep domain expertise in HL7, clinical workflows, payor rules—updated annually.

| Step                   | Details                                                                                                                       |
|------------------------|-------------------------------------------------------------------------------------------------------------------------------|
| **Base model**         | LLaMA-13B or BioMedLM-2.7B (if available)                                                                                     |
| **Data sources**       | - MIMIC-III de-identified notes<br>- HL7 v2.x & FHIR specification corpora<br>- Clinical procedure manuals (CPT codes, payor docs) |
| **Fine-tuning method** | 1. SFT on clinician–bot dialogues (e.g. physician consult transcripts)<br>2. Conditional-generation exemplars for HL7 segments<br>3. FHIR resource construction tasks |
| **Hyperparams**        | LR = 2e-5, batch = 4, epochs = 5; context window = 4 K tokens                                                                 |
| **Quantization**       | FP16, optionally 4-bit via QLoRA                                                                                            |
| **Artifact**           | `models/healthcare-bot/`                                                                                                     |
| **Maintenance**        | Annual re-fine-tuning with updated dataset snapshots                                                                         |

---

## 5. Automation Agent Module

**Objective:** read/write automation scripts (PowerShell, Python, YAML) and orchestrate multi-step processes.

| Step                   | Details                                                                                                        |
|------------------------|----------------------------------------------------------------------------------------------------------------|
| **Base model**         | Same base as Coding module (GPT-NeoX or LLaMA)                                                                 |
| **Data sources**       | - GitHub repos of common automation (Ansible, PowerShell DSC, Azure CLI scripts)<br>- Home Assistant & Power Automate templates<br>- “How to automate X” blog posts |
| **Fine-tuning method** | LoRA + SFT on instruction→script pairs, with functional test verification                                       |
| **Hyperparams**        | LR = 1e-4, batch = 8, epochs = 3                                                                               |
| **Quantization**       | INT8; prune adapter weights if needed                                                                          |
| **Artifact**           | `models/automation-agent/`                                                                                     |
| **Inference**          | On workstation/server; for Pi/phone, distill a minimal adapter covering a core subset of actions               |

---

## Manual Training

To run the Silhouette training pipeline locally:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
accelerate config default --yes
accelerate launch training/train_silhouette.py --config config/train_config.yaml
ruff .
pytest -q
coverage html
```

Automated runs are configured through the [train.yml](../.github/workflows/train.yml) workflow.
