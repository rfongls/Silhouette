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

**Status:** scaffold with templates

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

* `<run>/active/ir_playbook.json` with incident-specific steps.

**Next Steps:**
- Flesh out tabletop inject library and scheduling.
- Add communication plan templates and contact tree.

---

## Phase 7 — Pentest Gates (Authorization & Scope)

**Skill:** `skills/cyber_pentest_gate.v1.wrapper:tool`

**Status:** scaffold

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

* `<run>/active/pentest_gate.json` when authorized.

**Next Steps:**
- Implement ownership verification via DNS TXT/HTTP.
- Record audit logs for gate decisions.

---

## Phase 8 — Recon & Active Testing (Safe Profiles)

**Skill:** `skills/cyber_recon_scan.v1.wrapper:tool`

**Status:** scaffold; **wired to CLI**

**CLI:**

```bash
python -m silhouette_core.cli security --ack-authorized pentest recon \
  --target sub.example.com \
  --scope-file docs/cyber/scope_example.txt
```

**Inputs (JSON):**

```json
{"target":"sub.example.com","scope_file":"docs/cyber/scope_example.txt","out_dir":"<run>"}
```

**Outputs:**

* `<run>/active/recon.json` containing an inventory stub.

**Next Steps:**
- Add scan profiles (`safe`, `version`, `full`) with rate limits.
- Normalize and enrich findings offline.

---

## Phase 9 — Network Forensics Toolkit

**Skill:** `skills/cyber_netforensics.v1.wrapper:tool`

**Status:** scaffold

**CLI:**

```bash
python -m silhouette_core.cli security --ack-authorized pentest netforensics --pcap sample.pcap
```

**Inputs (JSON):**

```json
{"pcap":"capture.pcap","out_dir":"<run>"}
```

**Outputs:**

* `<run>/active/netforensics.json` with placeholder fields.

**Next Steps:**
- Support tcpdump capture and Zeek/Suricata parsing.
- Enable TLS decryption and YARA/ClamAV triage.

---

## Phase 10 — Extensions (Future)

**Skill:** `skills/cyber_extension.v1.wrapper:tool`

**Status:** scaffold

**Inputs (JSON):**

```json
{"feature":"cloud","out_dir":"<run>"}
```

**Outputs:**

* `<run>/active/cyber_extension.json` with `status: "not_implemented"`.

**Next Steps:**
- Explore cloud posture modules and SOAR export hooks.

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
  --scope-file docs/cyber/scope_example.txt
```

---

## Tests

* `tests/test_security_pentest.py` verifies:

  * Out-of-scope denial
  * In-scope success + result under `<run>/active/recon.json`

