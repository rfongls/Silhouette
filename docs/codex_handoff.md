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
