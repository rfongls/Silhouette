# Handoff & Developer Guide

This guide centralizes all “handoff” instructions for the Silhouette Core training pipeline, including:

- Cloning & branching via GitHub UI and CLI
- Generating Stage 1 dataset with Codex
- Merging multi-teacher outputs
- Evaluating the student model
- Training & quantizing the student adapter

---

## 1. Repository Setup

### A. GitHub Web UI
1. Navigate to: `https://github.com/your-org/Silhouette`.
2. Click on the **Branch** dropdown (default: `main`).
3. Type a new branch name (e.g., `feature/stage1-training-pipeline`) and press **Enter**.
4. To add/edit files: browse to a folder, click **Add file → Create new file** or **Upload files**, or click the pencil icon on existing files.
5. Commit changes by filling in the commit message and selecting **Commit directly to [your-branch]**.
6. Click **Compare & pull request**, fill in title/description, then **Create pull request**.
7. After review, click **Merge pull request** and **Confirm merge**. Optionally delete the branch.

### B. Command Line Interface (CLI)
```bash
# Clone the repo
git clone git@github.com:your-org/Silhouette.git
cd Silhouette

# Create & switch to feature branch
git checkout -b feature/stage1-training-pipeline

# Make edits locally (add or update files)
git add .
git commit -m "Add training pipeline handoff docs"

# Push to GitHub
git push origin feature/stage1-training-pipeline
# Open a PR via GitHub UI or GitHub CLI
```

---

## 2. Stage 1: Codex Dataset Expansion

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

---

## 3. Merge Multi-Teacher Outputs

1. Input: `modules/reasoner/teacher_outputs.jsonl`
2. Script: `silhouette_core/merge_teacher_outputs.py`
3. Handoff: see `training_data/reasoner/CODEX_HANDOFF_MERGE.md`
4. Run:

   ```bash
   python silhouette_core/merge_teacher_outputs.py \
     --input modules/reasoner/teacher_outputs.jsonl \
     --output modules/reasoner/distill_data.jsonl
   ```

---

## 4. Evaluate Student Model

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

---

## 5. Train & Quantize Student

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

---

## 6. CI Integration

Ensure your GitHub Actions workflow (`.github/workflows/train_reasoner.yaml`) covers all above steps in sequence and fails if evaluation metrics drop below threshold.

---
