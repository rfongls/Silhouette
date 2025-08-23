# GitHub Issues – Next Phase Roadmap (PR‑4 … PR‑9)

## 1. PR-4: JS/TS AST + Unified Dependency Graph
**Goal**
Parse `.ts/.tsx/.js/.jsx` sources and merge their dependencies with Python into a single repo graph.

**Scope**
- Implement `silhouette_core/lang/js_parser.py` using **tree-sitter** (preferred) or TypeScript compiler API.
- Extend `silhouette_core/graph/dep_graph.py` to merge Python + JS/TS nodes/edges.
- Detect exports/imports, symbol table, and file-level dependencies.
- Update repo map pipeline so `language_counts` includes JS/TS.

**Acceptance Criteria**
- Fixture repo at `tests/fixtures/js_ts_repo/` with simple imports/exports.
- Unit tests assert expected graph nodes and edges across languages.
- `silhouette repo map <repo>` shows `detected_languages` including `"ts"`/`"js"` when present.
- `ruff check` and `pytest -q` pass.

**Labels:** graph, languages, priority-high, PR-4
**Milestone:** PR-4 JS/TS Graph

## 2. PR-5: Language‑Aware Chunking + Local Embeddings Index
**Goal**
Improve retrieval quality and scale with deterministic, overlapping chunks and a local embeddings store.

**Scope**
- Add `silhouette_core/chunking.py` with chunkers for `.py` and `.ts/.js` (+ fallback text), configurable overlap.
- Integrate with `silhouette_core/embedding_engine.py` using SQLite or FAISS for local storage.
- Reindex on file change using mtime/hash checks.
- Provide a small retrieval smoke test on fixtures.

**Acceptance Criteria**
- Unit tests: stable chunk counts, correct overlap, deterministic output.
- Embedding store persists and reloads; reindex updates only changed files.
- `pytest -q` and `ruff check` pass.

**Labels:** retrieval, embeddings, priority-high, PR-5
**Milestone:** PR-5 Chunking & Embeddings

## 3. PR-6: Retrieval Planner + CLI Analyses
**Goal**
Route questions to the most relevant files/symbols via (graph + embeddings) and expose analyses via CLI.

**Scope**
- Implement `silhouette_core/retrieval/planner.py` to rank files/symbols combining dep-graph proximity and embedding scores.
- Add CLI commands:
  - `silhouette analyze hotpaths`
  - `silhouette analyze service <path>`
  - `silhouette suggest tests <path>`
  - `silhouette summarize ci`
- Each command outputs human-readable text and `--json`.

**Acceptance Criteria**
- Tests exercise planner ranking on fixture repos (label small gold sets to measure Precision@k/Recall@k).
- CLI help shows new commands; `--json` returns structured output.
- `pytest -q` and `ruff check` pass.

**Labels:** cli, analysis, retrieval, priority-high, PR-6
**Milestone:** PR-6 Retrieval & Analyses

## 4. PR-7: Dev Cards + HTML Repo Map Report
**Goal**
Produce a human-friendly HTML report with service Dev Cards and repo stats.

**Scope**
- Enrich `repo_map.json` (entrypoints, top centrality nodes, test coverage summary, CI tools).
- Render `artifacts/<ts>/repo_map.html` (cards per service/module, graphs/stats sections).
- Keep output lightweight (no heavy front-end build).

**Acceptance Criteria**
- Golden-file tests assert key sections render (languages, service cards, stats).
- `silhouette repo map <repo>` emits both JSON and HTML artifacts.
- `pytest -q` and `ruff check` pass.

**Labels:** reporting, graph, priority-medium, PR-7
**Milestone:** PR-7 Dev Cards & HTML

## 5. PR-8: Propose‑Patch (Dry‑Run) + Impact Set + PR Body
**Goal**
Safely generate a patch (without writing), compute impacted modules/tests/docs, and produce a merge-ready PR body.

**Scope**
- `silhouette_core/patch/propose.py`: build unified diff from a goal + hints, **no writes** by default.
- `silhouette_core/impact/impact_set.py`: map touched code → tests/docs to run/update.
- Respect `policy.yaml` (protected paths/branches); write mode only when explicitly enabled.

**Acceptance Criteria**
- CLI: `silhouette propose patch --goal "..."` writes `artifacts/<ts>/proposed_patch.diff` and prints preview.
- Impact set lists tests to run; subset passes on fixture repos.
- `pytest -q` and `ruff check` pass.

**Labels:** automation, patch, policy, priority-medium, PR-8
**Milestone:** PR-8 Propose Patch

## 6. PR-9: Offline Validation Script & Documentation
**Goal**
Prove the core workflow runs without network access.

**Scope**
- Add `scripts/offline_check.sh` to simulate no-network and run: repo map → analyze → suggest → summarize on fixtures.
- Document the procedure and prerequisites in `docs/offline_parity.md`.
- Optionally provide a dev container or local wheelhouse instructions for tool caching.

**Acceptance Criteria**
- Script completes on a clean machine with network disabled.
- Documentation is clear enough for external contributors.
- `ruff check` passes; no tests required beyond a minimal smoke run.

**Labels:** offline, docs, priority-low, PR-9
**Milestone:** PR-9 Offline Validation

## 7. Coordination: Wire CLI run-recording, link docs, and finalize PR-3 merge
**Goal**
Close out PR-3 cleanly and prepare the tree for PR-4..PR-9 execution by Codex.

**Checklist**
- [ ] Ensure `repo map` is wrapped with `record_run(...)` (create + save both inside context).
- [ ] README links to `docs/repo_integration.md` and `docs/hl7_testing.md`.
- [ ] `ruff check silhouette_core tests` passes.
- [ ] `pytest -q` passes or skips HL7 versions unsupported by local `hl7apy`.
- [ ] `bash scripts/ci_local.sh` returns 0.

**Notes**
Set milestones for downstream PRs before running the issue creation script.

**Labels:** coordination, docs, priority-high, PR-3
**Milestone:** PR-3 HL7 & CI
