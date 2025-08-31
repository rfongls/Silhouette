# Cybersecurity Skill

## Quickstart

```bash
python -m silhouette_core.cli security evidence --source docs/fixtures/security_sample --dry-run
python -m silhouette_core.cli security scan --tool trivy --target docs/fixtures/app --use-seed
# replace <ts> with the created run folder
python -m silhouette_core.cli security map-controls --framework cis_v8 --evidence out/security/<ts>/evidence
python -m silhouette_core.cli security report --format html --in out/security/<ts> --offline
```

## Command Matrix

| Command | Description |
|---------|-------------|
| evidence | Collect and redact evidence |
| map-controls | Map evidence to controls |
| scan | Run defensive scanners |
| report | Generate offline report |
| assess, pcap, ids | Stubs |
| pentest | Stub (requires --ack-authorized) |

## Safety Notes
- All actions are offline by default.
- Active commands require explicit acknowledgment with `--ack-authorized`.
- Outputs stored under `out/security/<UTC_ISO>`.
