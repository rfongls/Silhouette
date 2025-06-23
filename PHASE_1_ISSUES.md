
# 📋 Phase 1 Issues – Bootstrap Survival Core

This document lists all recommended GitHub issues to be created under the Phase 1 milestone.

---

### 🔧 Runtime & CLI
- **Add CLI fallback interface**  
  Build a simple REPL-based shell for offline user interaction.

- **Set up llama.cpp runtime**  
  Provide instructions and scripts to run `.gguf` models locally using CPU.

- **Integrate TinyLLaMA 1.1B GGUF**  
  Document the download/setup of a quantized open-source model.

---

### 🧠 Alignment Core
- **Implement alignment DSL loader**  
  Parse and apply logic from `values.dsl` to control assistant behavior.

- **Define core values and rules DSL**  
  Expand the `values.dsl` to include edge case handling and personality traits.

---

### 📦 Modularity & Expansion
- **Define module loader spec**  
  Use JSON/YAML to define dynamic module metadata (name, type, entrypoint).

- **Prototype sample module (math)**  
  Build a math handler module with fallback reasoning if model is unavailable.

---

### 🧱 Structure & Docs
- **Add initial README and philosophy docs**  
  Finalize and polish documentation files for the root of the repo.

- **Create GitHub Actions CI**  
  Add GitHub Action to run Python linter on each pull request.

- **Create CONTRIBUTING.md**  
  Add guidelines for issues, PRs, and code standards.

---

Each issue should be tagged with:
- Milestone: `Phase 1 – Bootstrap Survival Core`
- Labels: `enhancement`, `docs`, `infra`, `core`, or `good first issue` as appropriate
