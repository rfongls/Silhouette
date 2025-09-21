# Skills Registry (`skills/`)

This document enumerates skills available to the agent. Invoke a skill from the REPL with `use:<skill> <args>`.

## Index
| Skill | Purpose | Entry Point | Example |
|------|---------|-------------|---------|
| http_get_json | Fetch JSON from an HTTP endpoint with timeout | `tool(url, timeout=5.0)` | `use:http_get_json https://example.com/data` |
| research_read_pdf | Read a PDF and emit sectioned JSON | `tool(pdf_path)` | `use:research_read_pdf docs/file.pdf` |
| research_index | Insert PDF sections into SQLite FTS index | `tool(sections_json)` | `use:research_index <sections-json>` |
| research_search | Search the local research index | `tool(query, k=5)` | `use:research_search agent` |
| research_retrieve | Retrieve top-K passages for a query | `tool(payload)` | `use:research_retrieve {"query":"ai","k":3}` |
| research_cite | Format numeric citations from passages | `tool(passages_json)` | `use:research_cite <passages-json>` |
| cyber_nmap_scan | Run authorized Nmap scan on targets | `tool(payload)` | `use:cyber_nmap_scan {"target":"192.0.2.1"}` |
| cyber_zap_baseline | OWASP ZAP baseline scan for web target | `tool(payload)` | `use:cyber_zap_baseline {"target":"https://site"}` |
| cyber_trivy_scan | Container or directory vulnerability scan | `tool(payload)` | `use:cyber_trivy_scan {"image":"ubuntu:latest"}` |
| cyber_checkov_scan | Scan IaC configs using Checkov | `tool(payload)` | `use:cyber_checkov_scan {"path":"infra/"}` |
| cyber_cis_audit | Run basic CIS-style host checks | `tool(payload)` | `use:cyber_cis_audit {}` |
| cyber_vuln_lookup | Lookup CVE details offline | `tool(payload)` | `use:cyber_vuln_lookup {"cve":"CVE-2023-0001"}` |
| cyber_checklist_cdse | Return CDSE/NIST checklist items | `tool(payload)` | `use:cyber_checklist_cdse {"domain":"identity"}` |
| cyber_reference_cdse | Lookup CDSE/NIST reference sections | `tool(payload)` | `use:cyber_reference_cdse {"id":"AC-1"}` |
| cyber_control_mapper | Map findings to control families | `tool(payload)` | `use:cyber_control_mapper {"finding":"..."}` |
| cyber_task_orchestrator | Orchestrate scans and compile report | `tool(payload)` | `use:cyber_task_orchestrator {"target":"https://site"}` |
| cyber_report_writer | Compile Markdown report from findings | `tool(payload)` | `use:cyber_report_writer {"findings":[]}` |

## Details
### http_get_json
Fetch JSON from a URL. Returns a compact JSON string or an error description.

### research_read_pdf
Input: local PDF path. Output: JSON list of `{doc_id, section_id, text}` entries.

### research_index
Accepts JSON sections and writes them to `artifacts/index/research.db`.

### research_search
Arguments: `query` string and optional `k` (default 5). Returns ranked passages.

### research_retrieve
Payload JSON `{"query": "...", "k": 3}` returns passage objects.

### research_cite
Takes passages JSON and returns numbered citation mappings.

### cyber_nmap_scan
Payload includes `target`, optional `scope_file`, and `timing`. Runs containerized Nmap and returns result path.

### cyber_zap_baseline
Payload `{"target": "https://host"}` runs OWASP ZAP baseline scan.

### cyber_trivy_scan
Payload `{"image": "repo:tag"}` or `{ "path": "dir" }` runs a Trivy vulnerability scan.

### cyber_checkov_scan
Payload `{"path": "terraform/"}` scans IaC files with Checkov.

### cyber_cis_audit
Runs lightweight CIS-style host checks. Payload may include `{}` for defaults.

### cyber_vuln_lookup
Payload `{ "cve": "CVE-YYYY-NNNN" }` returns CVE metadata from a local cache.

### cyber_checklist_cdse
Payload `{ "domain": "identity" }` returns checklist items for a domain.

### cyber_reference_cdse
Payload `{ "id": "AC-1" }` returns reference text and citation info.

### cyber_control_mapper
Payload with finding details returns mapped control families.

### cyber_task_orchestrator
Coordinates scans (e.g., Nmap + ZAP) and returns a report path.

### cyber_report_writer
Consumes findings/controls data and emits a Markdown report path.

## Related
- Interop flow & trays → `docs/ui/interop-flow.md`
- Reporting (Validate) → `docs/reporting/validate.md`
- Reporting (ACKs) → `docs/reporting/mllp-acks.md`
