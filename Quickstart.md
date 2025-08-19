# 🚀 Silhouette Core Quickstart

A terse path from install → run → eval → train → release.
Follow the ten steps below and see [docs/User_Guide.md](docs/User_Guide.md) for full detail.

1. **Clone & Install**
   ```bash
   git clone https://github.com/your-org/Silhouette.git
   cd Silhouette
   pip install -e .[all]
   ```
2. **Start the Agent REPL**
   ```bash
   silhouette run --profile profiles/core/policy.yaml
   ```
3. **Try a Skill**
   ```
   > use:calc 6*7
   ```
4. **Run Basic Evals**
   ```bash
   silhouette eval --suite eval/suites/basics.yaml
   ```
5. **Capture Runtime Traces**
   ```bash
   ENABLE_RUNTIME_EVAL=1 silhouette build-runner --suite eval/suites/dev_python_runtime.yaml
   ```
6. **Promote Traces**
   ```bash
   make traces-promote
   ```
7. **Train a Student (SFT)**
   ```bash
   silhouette train --mode sft --cfg config/train.yaml
   ```
8. **Distill with Teacher (KD)**
   ```bash
   silhouette train --mode kd --cfg config/train.yaml
   ```
9. **Quantize & Probe Latency**
   ```bash
   silhouette quantize --method int8 --src models/student-core-kd --out models/student-core-int8
   SILHOUETTE_EDGE=1 STUDENT_MODEL=models/student-core-int8 silhouette latency
   ```
10. **Release & License**
    ```bash
    silhouette selfcheck
    make gates
    silhouette license --customer-id ORG-1234
    ```

You're done! Tag your release and publish artifacts as outlined in [RELEASE.md](RELEASE.md).
