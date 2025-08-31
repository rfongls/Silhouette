# Cybersecurity Skill — Next Phases (Authorized Defensive + External Pentest)

> Scope: full-spectrum, **authorized** security automation for internal defense and externally scoped penetration testing.  
> Guardrails: any active action requires explicit authorization + scoped targets; all runs are throttled, logged, and reversible where possible.  
> Offline-first: all modules must run locally with seed data/caches; network sync (CVE, KEV, NVD, CISA) optional only.

Legend: **Implement** (what to build) • **Test** (how to verify) • **DoD** (Definition of Done)

---

## Phase 0 — Policy & Scaffold
- **Implement:** repo layout (`skills/cybersecurity/`, `docs/skills/cybersecurity/`), policy banner, global **`--ack-authorized`** gate.
- **Test:** invoking any active command without the flag exits with guidance.
- **DoD:** safety gate enforced in all active subcommands.

---

## Phase 1 — CLI Surface & Skill Manifest
- **Implement:** CLI group `security` with subcommands:  
  - `assess`, `evidence`, `map-controls`, `report` (defense)  
  - `scan` (defense posture)  
  - `pentest` (external, gated) with subcommands `recon`, `net-survey`, `dast`, `api`  
  - `capture`, `pcap` (decode/extract/tls-decrypt/stats/triage), `ids` (zeek|suricata)  
  - Global flags: `--scope <file|cidr|domains>`, `--out out/security`, `--ack-authorized`
- **Test:** `python -m silhouette_core.cli security -h` shows commands; each subcommand supports `--dry-run`.
- **DoD:** CLI parses; dry-run writes stubs.

---

## Phase 2 — Evidence Capture (Defensive)
- **Implement:**  
  - Collect authorized artifacts (logs/configs/IaC/cloud posture) with PII redaction.  
  - Bundle + hash artifacts.  
  - **NEW:** generate evidence ZIP pack (`out/security/evidence_packs/*`) with:  
    - Raw artifacts  
    - Normalized JSON (`findings_normalized.json`)  
    - Control mapping JSON  
    - Report (`.md`, `.html`, `.pdf`)  
- **Test:** run against sample dirs; verify redaction, hashes, and ZIP integrity.
- **DoD:** `security evidence --source <path>` writes bundles and packs.

---

## Phase 3 — Controls Mapping (Multi-Framework)
- **Implement:**  
  - YAML maps under `configs/security/controls/*.yaml`.  
  - Produce coverage matrix with evidence anchors.  
  - Frameworks: **NIST CSF, CDSE, NIST 800-53, CIS v8, HIPAA §164, ISO 27001, PCI DSS**.  
  - Offline cache of all mappings.  
- **Test:** synthetic evidence triggers expected controls across frameworks; missing evidence marked.
- **DoD:** `security map-controls --framework nist_csf` and others emit CSV/HTML.

---

## Phase 4 — Defensive Scanners (Read-only Wrappers)
- **Implement:**  
  - Wrappers for:  
    - ✅ Trivy (images/IaC)  
    - ✅ Checkov  
    - ✅ CIS audit  
    - **NEW:** OpenVAS (offline mode with seed DB)  
    - **NEW:** Grype (container image vuln scan)  
    - **NEW:** tfsec, kics (IaC misconfig checks)  
    - **NEW:** Lynis (Linux audit), Windows baselines (PowerShell/CIS-CAT Lite)  
    - **NEW:** Secrets scanning (gitleaks/trufflehog)  
    - **NEW:** SCA (pip-audit, npm audit)  
- **Test:** run on seeded samples; ensure NO external scanning by default.
- **DoD:** `security scan --tool <scanner>` emits SARIF/JSON locally.

---

## Phase 5 — Risk Scoring & Reporting
- **Implement:**  
  - CVSS/OWASP scoring, business impact notes.  
  - Reports in Markdown → HTML → PDF (with offline renderer like `weasyprint`).  
  - Sections: exec summary, severity counts, detailed findings, control mappings, references, appendix.  
  - Severity heatmaps/charts generated offline (matplotlib).  
- **Test:** seeded findings yield stable scorecards; evidence links resolve.
- **DoD:** `security report --format html|pdf` writes to `out/security/report/*`.

---

## Phase 6 — Incident Response Playbooks & Tabletop
- **Implement:** runbooks (ransomware/credential/PII), tabletop injects, comms plan.
- **Test:** render playbook pack; check section completeness.
- **DoD:** `security report --playbook ransomware` outputs checklist.

---

## Phase 7 — Pentest Gates (Authorization & Scope)
- **Implement:**  
  - Require **auth doc** (`--auth-doc`)  
  - Require **scope file**  
  - Ownership verification (DNS TXT/HTTP well-known/allowlist)  
  - Global kill-switch, deny-lists, throttles, schedule windows  
- **Test:** any `security pentest *` without gates → exit; with gates → run.
- **DoD:** gates enforced and audited.

---

## Phase 8 — Recon & Active Testing (Nmap/DAST/API; Safe Profiles)
- **Implement:**  
  - **Recon:** passive DNS/TLS/HTTP inventory.  
  - **Nmap:** profiles `safe`/`version`/`full` (last requires risk ack).  
  - **DAST/API:** bounded crawler/fuzzer with excludes, auth support, 429/5xx backoff.  
  - **NEW:** Normalize findings via schema + enrich with CVE cache, KEV list, MITRE ATT&CK mapping (all offline-first with seeded datasets).  
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
- **Test:** seeded PCAPs produce flows, alerts, decrypted sessions (when keys provided), triage hits.  
- **DoD:** end-to-end pipeline reproducible offline.

---

## Phase 10 — Extensions (Future)
- **Implement:**  
  - Cloud security posture mgmt (ScoutSuite, Prowler; offline configs where possible).  
  - SOAR connectors (export to Splunk/ELK/Jira; offline file export supported).  
  - AI-assisted triage: deduplicate findings, prioritize by exploitability.  
- **Test:** offline datasets confirm outputs without network.  
- **DoD:** extensions optional, gated by configs.
