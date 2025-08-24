# Codex Training & Cleanup Handoff

**Purpose:**  
1. Audit the entire Silhouette Core repo.  
2. Remove irrelevant/unused files from the core framework.  
3. Ensure both **automated** CI and **manual** training modules are wired and documented.
4. Prepare everything for smooth training via Hugging Face.

---

## 1. Repo Inspection

- Traverse the root and subdirectories:
  - Identify any files or folders not referenced by code, docs, or CI.
  - Flag large binary assets (e.g., legacy models, datasets) that belong in separate storage.
- Generate a short report (`cleanup_report.md`) listing:
  - Unused scripts, configs, tests, or docs.
  - Deprecated modules under `/modules/` or `/silhouette_core/`.
  - Any `TODO` markers or commented-out code blocks that need attention.

---

## 2. Cleanup

Based on `cleanup_report.md`:

- **Remove**:
  - Unreferenced scripts (e.g., old prototype trainers, deprecated utilities).
  - Stale docs (e.g., draft handoffs you’ve already replaced).
  - Test files covering removed/archived functionality.
- **Archive**:
  - Move any still-valuable but infrequently used assets into an `archive/` folder at repo root.
  - Update `.gitignore` to exclude `archive/` from normal CI workflows.
- **Prune**:
  - Run `ruff --select F` to detect unused imports; auto-fix where safe.
  - Run `pytest --disable-warnings -q` and ensure that only active tests remain; remove empty test stubs.

---


## 3. Manual Training Module

Under `docs/manual_training_guide.md`:

1. **Confirm** there’s a dedicated section for manual training (local runs).
2. **Add** explicit commands to:
   - Create & activate `.venv`
   - Install both `requirements.txt` & `requirements-dev.txt`
   - Run `accelerate config` once for defaults
   - Run `accelerate launch training/train_silhouette.py --config config/train_config.yaml`
   - Lint (`ruff .`), test (`pytest`), and coverage steps.
3. **Link** this guide in your README under a “Manual Training” heading.

---

## 5. Finalize & PR

- Commit all changes to a new branch named:  
`codex/repo-cleanup-and-training-setup`
- Create a **cleanup_report.md** in the root summarizing removed/archived items.
- Open a PR against `main` with:
- Title: “Repo cleanup & training modules audit”
- Description listing:  
  - Files removed/archived  
  - CI updates
  - Manual guide enhancements

Once merged, CI will validate the cleanup, run tests, and ensure training workflows are operational.

---

## ⚙️ Final Codex Prompt

```

You are Codex. Your tasks:

1. Audit the entire repo and produce `cleanup_report.md` listing unreferenced or deprecated files.
2. Remove/ archive items per the report.
3. Update `.github/workflows/train.yml` for explicit accelerate flags.
4. Verify/augment `docs/manual_training_guide.md` with manual training steps.
5. Link the manual guide in `README.md`.
6. Commit to branch `codex/repo-cleanup-and-training-setup` and open a PR.

```

---

## Appendix: Handoff & Developer Guide

This guide centralizes all “handoff” instructions for the Silhouette Core training pipeline, including cloning & branching, dataset generation, merging teacher outputs, evaluation, training, and CI integration.

### 1. Repository Setup

#### A. GitHub Web UI
1. Navigate to: `https://github.com/your-org/Silhouette`.
2. Click on the **Branch** dropdown (default: `main`).
3. Type a new branch name (e.g., `feature/stage1-training-pipeline`) and press **Enter**.
4. To add/edit files: browse to a folder, click **Add file → Create new file** or **Upload files**, or click the pencil icon on existing files.
5. Commit changes by filling in the commit message and selecting **Commit directly to [your-branch]**.
6. Click **Compare & pull request**, fill in title/description, then **Create pull request**.
7. After review, click **Merge pull request** and **Confirm merge**. Optionally delete the branch.

#### B. Command Line Interface (CLI)
```bash
git clone git@github.com:your-org/Silhouette.git
cd Silhouette
git checkout -b feature/stage1-training-pipeline
# make edits
git add .
git commit -m "Add training pipeline handoff docs"
git push origin feature/stage1-training-pipeline
```

### 2. Stage 1: Codex Dataset Expansion

1. Seed file: `training_data/reasoner/stage1_sample.jsonl` (5 examples).
2. Handoff prompt: see `training_data/reasoner/CODEX_HANDOFF_STAGE1.md`.
3. Run locally with the OpenAI CLI:
```bash
openai api completions.create \
  --model code-davinci-002 \
  --prompt "$(cat training_data/reasoner/stage1_sample.jsonl)\n\n$(sed -n '1,100p' training_data/reasoner/CODEX_HANDOFF_STAGE1.md)" \
  --max_tokens 25000 --temperature 0.0 \
  > training_data/reasoner/stage1_full.jsonl
```
4. Validate with compile-test script:
```bash
python scripts/validate_stage1.py --input training_data/reasoner/stage1_full.jsonl
```

### 3. Merge Multi-Teacher Outputs

1. Input: `modules/reasoner/teacher_outputs.jsonl`
2. Script: `silhouette_core/merge_teacher_outputs.py`
3. Handoff: see `training_data/reasoner/CODEX_HANDOFF_MERGE.md`
4. Run:
```bash
python silhouette_core/merge_teacher_outputs.py \
  --input modules/reasoner/teacher_outputs.jsonl \
  --output modules/reasoner/distill_data.jsonl
```

### 4. Evaluate Student Model

1. Test file: `training_data/reasoner/stage1_test.jsonl`
2. Script: `silhouette_core/evaluate_student.py`
3. Handoff: see `training_data/reasoner/CODEX_HANDOFF_EVAL.md`
4. Run:
```bash
python silhouette_core/evaluate_student.py \
  --model-path modules/reasoner/adapter/qlora4b \
  --test-file training_data/reasoner/stage1_test.jsonl \
  --output evaluation_results.json \
  --max-tokens 256 --temperature 0.0
```

### 5. Train & Quantize Student

1. Fine-tune via QLoRA:
```bash
accelerate launch train_adapter.py \
  --module reasoner --base-model <student-id> \
  --train-file training_data/reasoner/stage1_full.jsonl \
  --out-dir modules/reasoner/adapter \
  --batch-size 2 --epochs 3 --rank 8
```
2. Quantize:
```bash
python quantize_models.py \
  --input modules/reasoner/adapter --bits 4 \
  --out modules/reasoner/adapter/qlora4b
```

### 6. CI Integration

Ensure your GitHub Actions workflow (`.github/workflows/train_reasoner.yaml`) covers all above steps in sequence and fails if evaluation metrics drop below threshold.

