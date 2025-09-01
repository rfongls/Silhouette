# Cybersecurity Skill — Next Phases (Authorized Defensive + External Pentest)

> Scope: full-spectrum, **authorized** security automation for internal defense and externally scoped penetration testing.  
> Guardrails: any active action requires explicit authorization + scoped targets; all runs are throttled, logged, and reversible where possible.  
> Offline-first: all modules must run locally with seed data/caches; network sync (CVE, KEV, NVD, CISA) optional only.

Legend: **Implement** (what to build) • **Test** (how to verify) • **DoD** (Definition of Done)

## Phase 0 — Policy & Scaffold ✅

* **Implement:** repo layout (`skills/cybersecurity/`), policy banner, global `--ack-authorized` gate.
* **Test:** invoking any active command without the flag exits with guidance.
* **DoD:** safety gate enforced in all active subcommands.

---

## Phase 1 — CLI Surface & Skill Manifest ✅

* **Implement:** CLI group `security` with subcommands (`evidence`, `map-controls`, `scan`, `report`, `pentest`, `assess`, `pcap`, `ids`).
* **Test:** `python -m silhouette_core.cli security -h` shows commands; each supports `--dry-run`.
* **DoD:** CLI parses; dry-run writes stubs.

---

## Phase 2 — Evidence Capture (Defensive) ✅

* **Implement:** collect authorized artifacts (logs/configs/IaC/cloud posture) with PII redaction; bundle + hash.
* **Test:** run against sample dirs; verify redaction and checksums.
* **DoD:** `security evidence --source <path>` writes bundles + evidence pack zip.

---

## Phase 3 — Controls Mapping (Multi-Framework) ✅

* **Implement:** YAML maps under `configs/security/controls/*.yaml`; produce coverage matrix (JSON/HTML/CSV).
* **Test:** seeded evidence triggers expected controls; missing evidence marked.
* **DoD:** `security map-controls --framework cis_v8` emits coverage artifacts.

---

## Phase 4 — Defensive Scanners (Read-only Wrappers) ✅

* **Implement:** wrappers for Trivy, Checkov, Grype, tfsec, kics, lynis, gitleaks, pip-audit, npm-audit.
* **Test:** run on seeded samples; ensure NO external scanning by default.
* **DoD:** `security scan --tool <scanner>` emits SARIF/JSON locally.

---

## Phase 5 — Risk Scoring & Reporting ✅

* **Implement:** severity counts, CVSS/OWASP scoring, CVE/KEV enrichment, HTML/MD reporting.
* **Test:** seeded findings yield stable scorecards; evidence links work.
* **DoD:** `security report --format html --offline` writes report pack.

---

## Phase 6 — Incident Response Playbooks & Tabletop
- **Implement:**
  - Draft runbooks for ransomware, credential compromise, and PII exposure. ✅
  - Build tabletop inject library and schedule planner. ✅
  - Define communication plan and contact tree templates. ✅
  - Scaffold stub module `skills/cyber_ir_playbook`. ✅
 - **Test:** render playbook pack; check section completeness.
 - **DoD:** `security --ack-authorized pentest playbook --incident ransomware` outputs checklist.

---

## Phase 7 — Pentest Gates (Authorization & Scope)
- **Implement:**
  - Enforce submission of **auth doc** (`--auth-doc`). ✅
  - Require **scope file** detailing allowed targets. ✅
  - Ownership verification via DNS TXT, HTTP well-known, or allowlist entries.
  - Global kill-switch. ✅
  - Deny-lists, throttles, schedule windows.
  - Audit log recording for all gate decisions. ✅
  - Scaffold stub module `skills/cyber_pentest_gate`. ✅
- **Test:** any `security pentest *` without gates → exit; with gates → run.
- **DoD:** gates enforced and audited.

---

## Phase 8 — Recon & Active Testing (Nmap/DAST/API; Safe Profiles)
- **Implement:**
  - **Recon:** passive DNS/TLS/HTTP inventory. ✅
  - **Recon profiles:** `safe`/`version`/`full` with rate limits. ✅
  - **Nmap:** profiles `safe`/`version`/`full` (last requires risk ack).
  - **DAST/API:** bounded crawler/fuzzer with excludes, auth support, 429/5xx backoff.
  - **NEW:** Normalize findings via schema + enrich with CVE cache, KEV list, MITRE ATT&CK mapping (all offline-first with seeded datasets).
  - Scaffold stub module `skills/cyber_recon_scan`. ✅
- **Test:** scans on lab scope respect rate limits; produce inventory & enriched findings.
- **DoD:** JSON inventory & findings saved; enrichment offline works.

---

## Phase 9 — Network Forensics Toolkit
- **Implement:**
  - **Capture:** tcpdump/dumpcap rotate + index.
  - **Decode/extract:** tshark to flows/fields; export HTTP objects.
  - **IDS:** Zeek/Suricata normalize to CSV/Parquet.
  - **TLS decrypt:** SSLKEYLOGFILE support; limitations documented.
  - **Triage:** YARA/ClamAV on extracted files; anomaly stats (offline z-score models).
  - **Flow counts** from PCAPs (packet/flow analysis). ✅
  - Scaffold stub module `skills/cyber_netforensics`. ✅
- **Test:** seeded PCAPs produce flows, alerts, decrypted sessions (when keys provided), triage hits.
- **DoD:** end-to-end pipeline reproducible offline.

---

## Phase 10 — Extensions (Future)
- **Implement:**
  - Cloud security posture mgmt (ScoutSuite, Prowler; offline configs where possible).
  - SOAR connectors (export to Splunk/ELK/Jira; offline file export supported).
  - AI-assisted triage: deduplicate findings, prioritize by exploitability.
  - Scaffold stub module `skills/cyber_extension`. ✅
- **Test:** offline datasets confirm outputs without network.
- **DoD:** extensions optional, gated by configs.
