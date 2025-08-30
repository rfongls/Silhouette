# Cybersecurity Skill — Next Phases (Authorized Defensive + External Pentest)

> Scope: full-spectrum, **authorized** security automation for internal defense and externally scoped penetration testing.  
> Guardrails: any active action requires explicit authorization + scoped targets; all runs are throttled, logged, and reversible where possible.

Legend: **Implement** (what to build) • **Test** (how to verify) • **DoD** (Definition of Done)

---

## Phase 0 — Policy & Scaffold
- **Implement:** repo layout (`skills/cybersecurity/`, `docs/skills/cybersecurity/`), policy banner, global **`--ack-authorized`** gate.
- **Test:** invoking any active command without the flag exits with guidance.
- **DoD:** safety gate enforced in all active subcommands.

## Phase 1 — CLI Surface & Skill Manifest
- **Implement:** CLI group `security` with subcommands:  
  `assess`, `evidence`, `map-controls`, `report` (defense);  
  `scan` (defense posture);  
  `pentest` (external, gated) with subcommands `recon`, `net-survey`, `dast`, `api`;  
  `capture`, `pcap` (decode/extract/tls-decrypt/stats/triage), `ids` (zeek|suricata).  
  Global flags: `--scope <file|cidr|domains>`, `--out out/security`, `--ack-authorized`.
- **Test:** `python -m silhouette_core.cli security -h` shows commands; each subcommand supports `--dry-run`.
- **DoD:** CLI parses; dry-run writes stubs.

## Phase 2 — Evidence Capture (Defensive)
- **Implement:** collect authorized artifacts (logs/configs/IaC/cloud posture) with PII redaction; bundle + hash.
- **Test:** run against sample dirs; verify redaction and checksums.
- **DoD:** `security evidence --source <path>` writes bundles to `out/security/evidence/*`.

## Phase 3 — Controls Mapping (NIST CSF / CIS)
- **Implement:** YAML maps under `configs/security/controls/*.yaml`; produce coverage matrix with evidence anchors.
- **Test:** synthetic evidence triggers expected controls; missing evidence marked.
- **DoD:** `security map-controls --framework nist_csf` emits CSV/HTML.

## Phase 4 — Defensive Scanners (Read-only Wrappers)
- **Implement:** wrappers for Trivy (images/IaC), K8s posture, SBOM analyzers; SARIF/JSON outputs.
- **Test:** run on seeded samples; ensure NO external scanning by default.
- **DoD:** `security scan --tool trivy --target <path>` emits SARIF/JSON.

## Phase 5 — Risk Scoring & Reporting
- **Implement:** CVSS/OWASP scoring, business impact notes; MD → PDF; exec & tech sections.
- **Test:** seeded findings yield stable scorecards; evidence links work.
- **DoD:** `security report --format pdf` writes `out/security/report/*`.

## Phase 6 — Incident Response Playbooks & Tabletop
- **Implement:** runbooks (ransomware/credential/PII); tabletop injects; comms plan.
- **Test:** render pack; check section completeness.
- **DoD:** `security report --playbook ransomware` outputs runnable checklist.

## Phase 7 — External Pentest Gates (Authorization & Scope)
- **Implement:** require **auth doc** (`--auth-doc`), **scope file**, **ownership verification** (DNS TXT/HTTP well-known/allowlist), global kill-switch, deny-lists, throttles, schedule windows.
- **Test:** any `security pentest *` without gates → exit; with gates → run.
- **DoD:** gates enforced and audited across pentest subcommands.

## Phase 8 — External Recon & Active Testing (Nmap/DAST/API; Safe Profiles)
- **Implement:**  
  **Recon:** passive DNS/TLS/HTTP inventory;  
  **Nmap:** profiles `safe`/`version`/`full` (last requires risk ack) with NSE categories;  
  **DAST/API:** bounded crawler/fuzzer with excludes, auth support, 429/5xx backoff.
- **Test:** scans on lab scope respect rate limits; produce inventory & findings with evidence.
- **DoD:** JSON inventory & findings saved; guardrails proven.

## Phase 9 — Network Forensics Toolkit (Capture → Decode → IDS → Decrypt → Triage)
- **Implement:**  
  **Capture:** tcpdump/dumpcap rotate + index;  
  **Decode/extract:** tshark to flows/fields; export HTTP objects;  
  **IDS:** Zeek/Suricata normalize to CSV/Parquet;  
  **TLS decrypt:** SSLKEYLOGFILE support; limitations documented;  
  **Triage:** YARA/ClamAV on extracted files; anomaly stats (z-score) on flows.
- **Test:** seeded PCAPs produce flows, alerts, decrypted sessions (when keys provided), triage hits.
- **DoD:** end-to-end pipeline reproducible on sample PCAPs.

---

## Self-Checks (must run before completing this phase set)
1. Active commands hard-fail without `--ack-authorized` **and** missing scope/verification (for pentest).
2. CLI help shows all commands/flags; dry-runs produce stubs.
3. Evidence bundles include hashes; redaction verified on PII samples.
4. Controls map resolves to a matrix with working anchors to evidence.
5. Defensive scans do not touch external hosts unless explicitly scoped.
6. Pentest modules confirm gates, throttle, deny-lists, and kill-switch.
7. PCAP pipeline runs on seeded traces: capture (or load), decode, IDS, (optional) decrypt, triage.
8. All outputs land under `out/security/**` with timestamps and provenance.

## Acceptance Criteria
- Evidence capture + controls mapping yield actionable matrices linked to artifacts.
- Defensive scanners and risk reports run locally; CI example blocks unsafe IaC/images.
- Pentest gates enforced; recon/scans/DAST/API produce scoped, throttled findings with evidence.
- PCAP toolkit completes full workflow on samples; decrypted sessions produced when keys available.
- Documentation (to be authored later) can reference accurate CLI help and outputs without gaps.
