# Cybersecurity Skill — Next Phases (Authorized Defensive + External Pentest)

> Scope: full-spectrum, **authorized** security automation for internal defense and externally scoped penetration testing.  
> Guardrails: any active action requires explicit authorization + scoped targets; all runs are throttled, logged, and reversible where possible.  
> Offline-first: all modules must run locally with seed data/caches; network sync (CVE, KEV, NVD, CISA) optional only.

Legend: **Implement** (what to build) • **Test** (how to verify) • **DoD** (Definition of Done)

**Completed:** Phases 0–5 (policy through reporting) delivered in offline-first baseline. The roadmap below tracks upcoming work for phases 6–10.

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
