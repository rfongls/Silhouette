# Silhouette Core — Installer Instructions & Quickstart

> **What is it?**
> Silhouette Core is a local, offline-friendly code agent. It builds a **repo map** (JSON + HTML), understands **Python + JS/TS** with a unified dependency graph, splits code into **deterministic chunks** with a **local embeddings index**, runs **analyses** (hotpaths, service reports, test suggestions, CI summaries), can **propose a dry-run patch** (diff + impact set + PR body), and ships an **offline check** to prove it works without internet.

---

## 1) Prerequisites

* **Python**: 3.10 (recommended)
* **Git**
* **Build tools**: a standard C/C++ build toolchain for your OS
* Optional (enables extras):

  * **Jinja2** (HTML reports) – installed via project deps
  * **networkx** (graph metrics) – installed via project deps
  * **Node/npm** only if the target repo needs it (Silhouette itself doesn’t)

> On Python 3.12, a compatibility shim is included for `typing.ForwardRef`. Python 3.10 is preferred.

---

## 2) Install

```bash
# clone
git clone <your-silhouette-core-repo-url>
cd silhouette-core

# virtual env
python3.10 -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate

# install (editable)
pip install -U pip
pip install -e .
# optional extras, if defined:
# pip install -e ".[html-report,faiss]"
```

---

## 3) Verify the install

```bash
ruff check silhouette_core tests
pytest -q
```

> HL7 tests will **auto-skip** unsupported versions (that’s OK).

---

## 4) Minimal config

* **Policy:** `policy.yaml` at repo root (default is **read-only**).
* **Artifacts:** Commands write under `artifacts/<YYYYMMDD_HHMMSS>/…`.

Environment knobs (optional):

* `SILHOUETTE_HL7_VERSIONS` – e.g. `2.5.1,2.7` (defaults to `2.3,2.4,2.5,2.5.1,2.6,2.7,2.7.1,2.8`; unsupported versions auto-skip)

---

## 5) First run (your repo)

```bash
# 5.1 Map the repo (JSON + HTML)
silhouette repo map /path/to/repo --json-out artifacts/repo_map.json --compute-hashes
ls artifacts/*/repo_map.json artifacts/*/repo_map.html   # open the HTML in a browser

# 5.2 Analyses (add --json for machine output)
silhouette analyze hotpaths --json
silhouette analyze service services/api --json      # adjust path for your repo
silhouette suggest tests src --json                 # file or directory
silhouette summarize ci --json                      # CI & Dockerfile summary

# 5.3 Dry-run a small change (no writes to the worktree)
silhouette propose patch --goal "Remove unused param and add null guard" --hint src/util.py
# Artifacts:
#   artifacts/<ts>/proposed_patch.diff
#   artifacts/<ts>/impact_set.json
#   artifacts/<ts>/proposed_pr_body.md

# 5.4 Replay the latest recorded run
bash scripts/repro.sh
```

---

## 6) Prove offline mode

Disconnect (or block network) and run:

```bash
bash scripts/offline_check.sh
```

The script runs **map → analyze → suggest → summarize** and **exits non-zero** on failure. It prints the exact **artifact folder** used.

---

## 7) Day-1 tuning (optional)

* Retrieval blend **alpha** (graph vs embeddings): try `0.25 / 0.5 / 0.75` and choose what returns the best results for your repo.
* Keep planner `top_k` in the **10–20** range initially.

---

## 8) Folder tour

```
silhouette_core/
  repo_map.py                 # builds repo_map.json
  report/html_report.py       # renders repo_map.html (self-contained)
  lang/js_parser.py           # JS/TS imports/exports/symbols (with line/col)
  graph/dep_graph.py          # unified Python + JS/TS dependency graph
  chunking.py                 # deterministic chunkers (Py, JS/TS, fallback)
  embedding_engine.py         # local SQLite embeddings index (stub embedder by default)
  retrieval/planner.py        # hybrid ranking (graph + embeddings)
  analysis/                   # hotpaths, service, suggest-tests, summarize-ci
  patch/                      # propose_patch (dry-run diff)
  impact/                     # compute impact set (modules → tests → docs)
  run_artifacts.py            # records silhouette_run.json
scripts/
  repro.sh                    # replay a recorded run (auto-picks latest)
  offline_check.sh            # offline validation (no network)
artifacts/<timestamp>/        # JSON/HTML/diff/PR body per run
policy.yaml                   # read-only default; protected paths enforced
```

---

## 9) Troubleshooting

**Ruff fails with SyntaxError in `js_parser.py`**
Use raw strings for regex (`r"...pattern..."`), avoid unbalanced `(`, and sanity-check:

```bash
python -m py_compile silhouette_core/lang/js_parser.py
ruff check --select E999 silhouette_core/lang/js_parser.py
```

**HL7 “UnsupportedVersion”**
Set `SILHOUETTE_HL7_VERSIONS="2.5.1,2.7"`, or run `pytest -q -m hl7` and let tests auto-skip unsupported versions.

**Python 3.12 typing crash**
Run `pytest` once so the ForwardRef shim loads; prefer Python 3.10.

**No HTML file appears**
Ensure Jinja2 is installed or pass `--html-out`. HTML generation runs by default inside the same `record_run` as JSON.

**Propose-patch returns “no targets”**
Your hints may be **protected** by policy. Try a non-protected path or adjust `policy.yaml` (dry-run still never writes).

---

## 10) What “good” looks like (quick checklist)

* [ ] `ruff check silhouette_core tests` → **OK**
* [ ] `pytest -q` → **OK** (HL7 may skip unsupported; OK)
* [ ] `silhouette repo map …` → emits **repo_map.json** + **repo_map.html**
* [ ] Analyses return meaningful JSON (hotpaths, service deps, test suggestions, CI plan)
* [ ] `silhouette propose patch …` → emits **diff**, **impact_set.json**, **proposed_pr_body.md**
* [ ] `bash scripts/offline_check.sh` → completes **with network disabled**

---

## 11) Notes on security & policy

* Default **read-only** posture; dry-run patching **never** writes to the worktree.
* `policy.yaml` enforces **protected paths** (e.g., CI workflows, keys). Proposals are filtered; the CLI notes any skipped hints.

---

*This document is intended to be saved as `docs/INSTALL_QUICKSTART.md` (or your installer instruction MD) so new users can install and run Silhouette Core in minutes.*
