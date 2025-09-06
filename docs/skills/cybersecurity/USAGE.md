# Cybersecurity Skill — Real-World Usage

> **TL;DR**: keep it authorized, scoped, and slow by default.

## UI Quick Start (Baseline)
- Open **Security Dashboard → Quick Start**
- Enter a target (e.g., `example.com`) and click **Run Baseline**
- The baseline runs **Gate ➜ Recon (safe)** and shows a readable table
- KPIs update instantly (Gate, Recon, Severities, Netforensics)
- Use **Load Demo** to populate KPIs offline if no target is available

## KPIs & History
- KPI bar summarizes recent artifacts under `out/security/**/active/`
- Trend points are persisted to `out/security/ui/index.json` and shown as sparklines on **Security → History**

## 1) Authorization & Scope

- Always require **written authorization** (PDF) from the asset owner. Pass its path as `auth_doc`.
- Maintain a **scope file** (e.g., `docs/cyber/scope_example.txt`) with allowed targets:
  ```
  example.com
  *.example.com
  sub.example.com
  ```
- Harden with env vars:
  - `CYBER_DENY_LIST=/path/deny.txt` — newline targets to deny
  - `CYBER_PENTEST_WINDOW=09:00-17:00` — **UTC** window; deny outside
  - `CYBER_THROTTLE_SECONDS=300` — cool-down between runs
  - `CYBER_KILL_SWITCH=true` — deny everything immediately

## 2) Happy-Path Flow (Gate → Recon → Forensics → IR)

### A) Gate
```python
from skills.cyber_pentest_gate.v1.wrapper import tool
print(tool('{"target":"sub.example.com","scope_file":"docs/cyber/scope_example.txt","auth_doc":"auth.pdf","out_dir":"out/security/runA"}'))
```

### B) Recon (profiles: safe | version | full)
```python
from skills.cyber_recon_scan.v1.wrapper import tool
print(tool('{"target":"sub.example.com","scope_file":"docs/cyber/scope_example.txt","profile":"version","out_dir":"out/security/runA"}'))
```
Emits **service inventory** and flags **KEV** for seeded CVEs (offline).

### C) Netforensics
```python
from skills.cyber_netforensics.v1.wrapper import tool
print(tool('{"pcap":"capture.pcap","out_dir":"out/security/runA"}'))
```
Writes packet/flow counts, basic alerts, and extracted artifacts stub.

### D) IR Playbook
```python
from skills.cyber_ir_playbook.v1.wrapper import tool
print(tool('{"incident":"ransomware","out_dir":"out/security/runA"}'))
```
Produces a runnable IR checklist with comms, inject schedule, and AAR prompts.

## 3) Operational Safety Guidelines

- Prefer **lab/staging** before production; emulate real targets where possible.
- Rate-limit scans; use maintenance windows; coordinate with owners.
- Log **every decision** and **audit** gate results to an immutable store.
- Redact sensitive data in outputs; keep artifacts under least privilege.
- Version and pin **offline seeds** (CVE/KEV) to ensure reproducibility.

## 4) Example Profiles

- **Staging sweep (safe):**
  - `CYBER_THROTTLE_SECONDS=60`, `profile=safe`
- **Light prod (version):**
  - Window 00:00–03:00 UTC (`CYBER_PENTEST_WINDOW=00:00-03:00`)
  - `CYBER_DENY_LIST` for sensitive assets
- **Full engagement (full):**
  - Only with explicit sign-off; validate in lab first

## 5) Offline Seeds and Scope (one-time)

```bash
mkdir -p data/security/seeds/cve data/security/seeds/kev docs/cyber
echo '{ "CVE-0001": {"summary":"Demo CVE for offline tests","severity":5} }' > data/security/seeds/cve/cve_seed.json
echo '{ "cves": ["CVE-0001"] }' > data/security/seeds/kev/kev_seed.json
printf 'example.com\n*.example.com\nsub.example.com\n' > docs/cyber/scope_example.txt
```

> Results are written under `out/security/<UTC_ISO>/active/` or the `out_dir` you supply.
