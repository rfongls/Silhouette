# \ud83d\udcd8 Silhouette Core \u2014 User Guide

Silhouette Core is a **survivable, modular, and scalable AI agent framework**.  
This guide explains **how to install, run, and use the agent end-to-end**: from running the CLI to training, compliance, and releasing governed artifacts.

---

## \ud83c\udf10 End-to-End Pipeline (At a Glance)

```mermaid
flowchart TD
    A[Install] --> B[Run Agent REPL]
    B --> C[Eval Skills & Languages]
    C --> D[Runtime Traces]
    D --> E[Curate Traces (Flywheel v2)]
    E --> F[Train Student (SFT)]
    F --> G[Distill w/ Teacher (KD)]
    G --> H[Quantize for Edge (INT8, ONNX, GGUF)]
    H --> I[Latency Probe]
    I --> J[Compliance & Regression Gates]
    J --> K[License Issuance + Watermark]
    K --> L[Release Artifacts]
```

---

## 1. What is Silhouette Core?

* A **self-hostable AI agent system**.
* Runs **offline-first** \u2014 no cloud/API dependencies required.
* Uses **skills** (tools) for capabilities (Python, Web, Java, .NET, Android, C++).
* Continuously improves itself through a **data flywheel** (eval \u2192 traces \u2192 training).
* Enforces **compliance, provenance, and licensing** at every step.
* Distills large models into **small agents** that can run on edge devices.

---

## 2. Installation

### Development mode

```bash
git clone https://github.com/your-org/Silhouette.git
cd Silhouette
pip install -e .[all]
```

### Runtime only

```bash
pip install silhouette-core
```

### Docker

```bash
docker run -it your-org/silhouette:latest
```

---

## 3. Running the Agent

Start the REPL:

```bash
silhouette run --profile profiles/core/policy.yaml
```

### 3.1 Using the Agent

The agent loop:

1. Reads input.
2. Checks persona alignment (`persona.dsl`).
3. Routes to a skill (`use:<tool> ...`) or generates text.
4. Logs result to `memory.jsonl`.

**Example session**

````
> Hello Agent
Agent: Hello! I\u2019m online and aligned.

> use:calc 9*9
Agent: 81

> Write a Python function to compute factorial
Agent:
```python
def factorial(n: int) -> int:
    return 1 if n <= 1 else n * factorial(n-1)
```

> [prompt violating persona rules]
> Agent: Sorry, I cannot help with that.
````

**As you train and add skills, the agent grows more capable.**

---

## 4. Skills

Skills extend the agent.

Registry: `skills/registry.yaml`

```yaml
- name: http_get_json
  version: v1
```

Usage:

```
> use:http_get_json https://api.example.com/data
```

**Research Toolpack flow**

```
> use:research_read_pdf docs/corpus/report_2023.pdf
> use:research_index <paste JSON>
> use:research_retrieve {"query":"telehealth rural outcomes","k":3}
> Summarize findings and include citations.
```

**Cybersecurity Toolpack**

Create a scope file and enable scanning:

```bash
export SILHOUETTE_PEN_TEST_OK=1
echo "192.168.1.10" > docs/cyber/scope_example.txt
```

Example REPL calls:

```
> use:cyber_nmap_scan {"target":"192.168.1.10","scope_file":"docs/cyber/scope_example.txt"}
> use:cyber_zap_baseline {"url":"https://intranet.example","scope_file":"docs/cyber/scope_example.txt"}
> use:cyber_trivy_scan {"dir":"docs/cyber"}
> use:cyber_checkov_scan {"dir":"docs/cyber"}
```

See [COMPLIANCE.md](../COMPLIANCE.md) for authorization rules.


## Cybersecurity Toolpack + CDSE/NIST

After indexing the CDSE content:

```bash
make cdse-index
```

Then run an orchestrated dry-run assessment:

```bash
export SILHOUETTE_PEN_TEST_OK=1
echo "192.168.1.10" > docs/cyber/scope_example.txt
silhouette run
> use:cyber_task_orchestrator {"task":"web_baseline","target":"https://in-scope.example","scope_file":"docs/cyber/scope_example.txt","dry_run":true}
```

The agent writes a Markdown report under `artifacts/cyber/reports/` with mapped controls and references.


---

## 5. Evaluations

Test behavior:

```bash
silhouette eval --suite eval/suites/basics.yaml
```

Cross-language runtimes (via Docker):

```bash
ENABLE_RUNTIME_EVAL=1 silhouette build-runner --suite eval/suites/dev_python_runtime.yaml
ENABLE_RUNTIME_EVAL=1 silhouette build-runner --suite eval/suites/dev_web_runtime.yaml
```

Research eval (citations required):

```bash
silhouette eval --suite eval/suites/research_grounded.yaml
```
Cybersecurity evals:

```bash
silhouette eval --suite eval/suites/cyber_safe_modes.yaml
silhouette eval --suite eval/suites/cyber_smoke.yaml
```


Gates include a `research` lane with a citation pass-rate threshold.
Gates also include a `cyber` lane for scan safety checks.

---

## 6. Training & Data Flywheel

1. Run evals \u2192 traces (`training_data/flywheel/<lane>/runtime.jsonl`).
2. Promote traces:

   ```bash
   make traces-promote
   ```
3. Train SFT:

   ```bash
   silhouette train --mode sft --cfg config/train.yaml
   ```
4. Distill KD:

   ```bash
   silhouette train --mode kd --cfg config/train.yaml
   ```

---

## 7. Quantization & Edge

```bash
silhouette quantize --method int8 --src models/student-core-kd --out models/student-core-int8
SILHOUETTE_EDGE=1 STUDENT_MODEL=models/student-core-int8 silhouette latency
```

---

## 8. Governance

* **Compliance**: SPDX scan, denylist (GPL/AGPL/MPL).
* **Regression Gates**: min pass-rates + latency budgets.
* **Provenance**: `WATERMARK.json` with commit, hash, license, customer_id.
* **Licensing**:

  ```bash
  silhouette license --customer-id ORG-1234
  ```

---

## 9. Scoreboards

Generate HTML + JSON dashboards:

```bash
python scripts/scoreboard.py
python scripts/scoreboard_history.py
```

Artifacts:

* `artifacts/scoreboard/index.html`
* `artifacts/scoreboard/history.html`
* `artifacts/gates/gate_summary.json`

---

## 10. Release Workflow

1. `silhouette selfcheck` + `make gates`
2. Version bump (`pyproject.toml`, `__init__.py`)
3. `git tag v1.0.0 && git push origin v1.0.0`
4. CI attaches:

   * wheel + sdist
   * scoreboards
   * compliance docs
   * watermark
   * license template

See [RELEASE.md](../RELEASE.md) for full checklist.

---

## 11. Where to Go Next

* [README.md](../README.md) \u2192 Overview
* [PHASES.md](../PHASES.md) \u2192 Roadmap
* [MILESTONES.md](../MILESTONES.md) \u2192 PR details
* [COMPLIANCE.md](../COMPLIANCE.md) \u2192 Governance
* [RELEASE.md](../RELEASE.md) \u2192 Release playbook
* [docs/HANDOFF_GUIDE.md](HANDOFF_GUIDE.md) \u2192 Codex automation
* [docs/Phase_10_Completion.md](Phase_10_Completion.md) \u2192 Phase 10 summary

---

With this **User Guide**, you have:
- A **visual pipeline** showing the full lifecycle.
- A **clear explanation of how to use it as an agent** (REPL loop, skills, alignment).
- End-to-end instructions for install \u2192 use \u2192 train \u2192 release.

