# Research Skill — Next Phases (Detailed, with Checkboxes)

> Purpose: literature discovery, grounded synthesis, citation-first answers; optional domain-model training. Respect licenses/robots; no paywalled scraping.

Legend: **Implement**, **Test**, **DoD**

---

## Phase 0 — Scaffold & Ethics
- **Implement:** layout (`skills/research/`, `docs/skills/research/`), sourcing policy (licensing, robots.txt, attribution).
- **Test:** policy renders; commands refuse disallowed sources.
- **DoD:** guardrails baked into CLI.

## Phase 1 — CLI Surface & Manifest
- **Implement:** `research` group: `search`, `ingest`, `index`, `answer`, `summarize`, `trace`. Global: `--sources <pubmed,arxiv,openalex,local>`, `--index out/research/index`.
- **Test:** `python -m silhouette_core.cli research -h` shows commands; dry-run emits stubs.
- **DoD:** CLI parses; stubs write outputs.

## Phase 2 — Connectors (Metadata-first)
- **Implement:** PubMed/Entrez, arXiv, OpenAlex, Crossref; local folder scan (PDFs).
- **Test:** `research search --q "topic"` returns JSONL metadata (title, authors, IDs, links).
- **DoD:** sources pluggable; rate-limit & retries in place.

## Phase 3 — PDF Parsing & Citation Grounding (Local Files)
- **Implement:** parse user-provided PDFs to structured JSON (sections, refs, page spans).
- **Test:** sample PDFs yield sectioned content with anchor offsets.
- **DoD:** `research ingest --path papers/` populates doc store with traceable spans.

## Phase 4 — Indexing & RAG (Section-Level)
- **Implement:** section-level embeddings; metadata (year, venue, DOI/PMID); BM25 fallback.
- **Test:** `research index --path store/` builds; queries return relevant chunks.
- **DoD:** `answer` uses retrieved spans only; aggregates per-source.

## Phase 5 — Answering & Summarization Policy
- **Implement:** retrieve → cite → synthesize pipeline; answers must include inline citations; JSON mode returns evidence list.
- **Test:** claims map to cited spans; empty evidence → safe refusal.
- **DoD:** `research answer --q` returns markdown + `[Author, Year, p.X]` style (or DOI-anchored) citations.

## Phase 6 — Workflows (PRISMA / Grant)
- **Implement:** PRISMA-style flow (identify→screen→include); export CSV + flowchart; grant/RFP boilerplates with parameters.
- **Test:** run small corpus; outputs deterministic; boilerplate fills required sections.
- **DoD:** `research summarize --corpus <tag>` emits PRISMA and/or grant skeletons.

## Phase 7 — Dataset Curation for Model Training
- **Implement:** build licensed Q/A+citations dataset; include negatives and contradiction examples.
- **Test:** splits (train/val) validated; license manifest compiled.
- **DoD:** `datasets/research_corpus/*` with README + license list.

## Phase 8 — Domain Model Training & Evals
- **Implement:** fine-tune small LLM on (question, evidence, answer+citations); eval: AttributionScore, citation precision/recall, refusal rate on no-evidence.
- **Test:** report metrics; regression gate in CI.
- **DoD:** `docs/skills/research/model_card.md` with metrics and safety behaviors.

## Phase 9 — Tooling & Runbook
- **Implement:** BibTeX/CSL JSON export (Zotero), Markdown/PDF outputs; caching policy; re-index schedule.
- **Test:** exports importable into Zotero; caches expire as configured.
- **DoD:** `docs/skills/research/runbook.md` complete.

---

## Self-Checks
1. CLI help reflects all commands; dry-run stubs created.
2. Source connectors respect licensing/robots; throttles/rate-limits active.
3. PDF parser yields sectioned JSON with anchors; ingestion keeps provenance.
4. Index built at section-level; RAG retrieves correct spans.
5. `answer` includes citations for every claim; empty evidence → safe refusal.
6. PRISMA flow reproducible; CSV and flowchart stable.
7. Dataset curated with license manifest; evals pass regression gate.
8. Exports (BibTeX/CSL/MD/PDF) open/import without errors.

## Acceptance Criteria
- Search/ingest/index/answer flows run locally with example commands for Windows/PowerShell/Bash (to be documented).
- All answers include citations to ingested or public sources.
- PRISMA workflow and grant skeletons generate end-to-end on a small corpus.
- Dataset + model card produced with safety notes; eval metrics reported.
