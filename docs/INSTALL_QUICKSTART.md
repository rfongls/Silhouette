# Silhouette Core — Installer Quickstart

> For a full index of guides and capability docs, see the [documentation index](./README.md).

## 1. Clone the repository
```bash
git clone https://github.com/example/Silhouette.git
cd Silhouette
```

## 2. Install dependencies
- **Python** 3.10+
- **Git**
- **Build tools** for your OS (e.g., Visual C++ Build Tools on Windows)

### Windows
```bat
py -m pip install -U pip
py -m pip install -r requirements.txt
```

### macOS/Linux
```bash
python3 -m pip install -U pip
python3 -m pip install -r requirements.txt
```

## 3. Start the agent
Launch the unified CLI REPL:
```bash
python -m silhouette_core.cli run
```
Inside the REPL try the built-in Python skill:
```text
python: print("hello, silhouette")
```
See [Skills.md](./Skills.md) for the full registry.

## 4. Quick Feature Menu
After startup, explore other capabilities:

- **Build a deployable clone**
  ```bash
  python -m silhouette_core.package_clone --version 1
  ```
  See [Package_Clone.md](./Package_Clone.md)

- **Train or fine-tune**
  ```bash
  python training/train_sft.py --cfg training/configs/train.yaml
  ```
  See [Training.md](./Training.md)

- **Quantize a model**
  ```bash
  python scripts/quantize.py --model path/to/model
  ```
  See [Quantization.md](./Quantization.md)

- **Validate HL7 files**
  ```bash
  python tools/hl7_qa.py tests/fixtures/hl7/sample_set_x.hl7 --rules tests/hl7/rules/rules.yaml --engine fast
  ```
  See [hl7_testing.md](./hl7_testing.md)

- **Run in offline mode**
  ```bash
  bash scripts/offline_check.sh
  ```
  See [Offline_Mode.md](./Offline_Mode.md)

- **Manage agents** — [Agents.md](./Agents.md)
- **Use skills** — [Skills.md](./Skills.md)
- **Policy profiles** — [Profiles.md](./Profiles.md)
- **Security tools** — [Security.md](./Security.md)
- **Evaluation & gates** — [Eval.md](./Eval.md)
- **Configuration** — [Config.md](./Config.md)
- **Artifacts** — [Artifacts.md](./Artifacts.md)

## Next steps
- Explore more features via the [documentation index](./README.md).
- To validate HL7 files and generate reports, see [hl7_testing.md](./hl7_testing.md) for complete run commands.
