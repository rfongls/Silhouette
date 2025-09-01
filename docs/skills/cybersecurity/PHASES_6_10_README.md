# Cybersecurity Skill — Phases 6–10 (Scaffold, Offline-First)

This document describes the **Phase 6–10** scaffolds for the Cybersecurity Skill. All modules are **offline-first** and **gated**. Any active behavior requires explicit authorization and scope.

---

## Safety & Guardrails

- **Authorization required** for pentest commands: pass `--ack-authorized` at the `security` CLI group.
- **Scope enforcement**: targets must appear in a scope file (see `docs/cyber/scope_example.txt`).
- **Offline-first**: no network calls; all outputs are produced locally under `out/security/<UTC_ISO>/...`.

---

## Phase 6 — Incident Response Playbooks & Tabletop

**Skill:** `skills/cyber_ir_playbook.v1.wrapper:tool`

**Status:** playbooks with communication plan, inject schedule, cross-team drills, and after-action templates

**CLI:**

```bash
python -m silhouette_core.cli security --ack-authorized pentest playbook --incident ransomware
```

**Inputs (JSON):**

```json
{"incident":"ransomware","out_dir":"<run>"}
```

Supported incidents: `ransomware`, `credential`, `pii` (falls back to generic).

**Outputs:**

* `<run>/active/ir_playbook.json` with incident-specific steps, communication plan, contacts, injects, schedule, drill simulation, and after-action template.

**Next Steps:**
- Expand inject scenarios and integrate with larger tabletop exercises.

---

## Phase 7 — Pentest Gates (Authorization & Scope)

**Skill:** `skills/cyber_pentest_gate.v1.wrapper:tool`

**Status:** scaffold with ownership verification, throttle controls, audit logging, deny-lists, schedule windows, and global kill switch

**CLI:**

```bash
python -m silhouette_core.cli security --ack-authorized pentest gate \
  --target sub.example.com \
  --scope-file docs/cyber/scope_example.txt \
  --auth-doc auth.pdf
```

**Inputs (JSON):**

```json
{"target":"example.com","scope_file":"docs/cyber/scope_example.txt","auth_doc":"auth.pdf","out_dir":"<run>"}
```

**Behavior:** Denies if target not in scope or missing/invalid `auth_doc`.

**Outputs:**

* `<run>/active/pentest_gate.json` and audit log when authorized.

**Next Steps:**
- Expand verification challenge types and throttle policies.

---

## Phase 8 — Recon & Active Testing (Safe Profiles)

**Skill:** `skills/cyber_recon_scan.v1.wrapper:tool`

**Status:** offline enrichment with Nmap profiles and stub DAST crawler

**CLI:**

```bash
python -m silhouette_core.cli security --ack-authorized pentest recon \
  --target sub.example.com \
  --scope-file docs/cyber/scope_example.txt \
  --profile version
```

**Inputs (JSON):**

```json
{"target":"sub.example.com","scope_file":"docs/cyber/scope_example.txt","profile":"version","out_dir":"<run>"}
```

**Outputs:**

* `<run>/active/recon.json` containing the selected profile, inventory, findings, and cache info.

**Next Steps:**
- Expand offline enrichment schema and coverage.

---

## Phase 9 — Network Forensics Toolkit

**Skill:** `skills/cyber_netforensics.v1.wrapper:tool`

**Status:** capture stub, flow indexing, artifact extraction, TLS key awareness, and basic alerts

**CLI:**

```bash
python -m silhouette_core.cli security --ack-authorized pentest netforensics --pcap sample.pcap
```

**Inputs (JSON):**

```json
{"pcap":"capture.pcap","out_dir":"<run>"}
```

**Outputs:**

* `<run>/active/netforensics.json` with packet and flow counts, alerts, TLS key status, and extracted artifacts.

**Next Steps:**
- Integrate full Zeek/Suricata pipelines and advanced triage models.

---

## Phase 10 — Extensions (Future)

**Skill:** `skills/cyber_extension.v1.wrapper:tool`

**Status:** stubs for cloud posture, SOAR export, and AI-assisted triage

**Inputs (JSON):**

```json
{"feature":"cloud","out_dir":"<run>"}
```

**Outputs:**

* `<run>/active/cyber_extension.json` describing requested extension feature.

**Next Steps:**
- Harden connectors and support additional platforms.

---

## Sample Scope File

See `docs/cyber/scope_example.txt`:

```
# exact domain
example.com
# wildcard subdomains allowed
*.example.com
# add IPs/CIDRs in future phases
```

---

## Developer Quickstart (Scaffold)

```bash
# 1) Create evidence, run seeds, map controls, report (Phases 0–5)
python -m silhouette_core.cli security evidence --source docs/fixtures/security_sample
latest=$(ls -d out/security/* | tail -n1)
python -m silhouette_core.cli security scan --tool trivy --target docs/fixtures/app --use-seed --out "$latest"
python -m silhouette_core.cli security map-controls --framework cis_v8 --evidence "$latest/evidence" --out "$latest"
python -m silhouette_core.cli security report --format html --in "$latest" --offline

# 2) Phase 8 scaffold (requires ack + scope)
python -m silhouette_core.cli security --ack-authorized pentest recon \
  --target sub.example.com \
  --scope-file docs/cyber/scope_example.txt \
  --profile safe
```

---

## Tests

* `tests/test_security_pentest.py` verifies:

  * Out-of-scope denial
  * In-scope success + result under `<run>/active/recon.json`

