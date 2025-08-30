# FHIR Testing

## Prereqs
- Python 3.12+
- `pip install -e .`
- Java 17 and `validators/validator_cli.jar` for HAPI
- HL7 fixtures under `tests/data/hl7/`
- Map files under `maps/`

## Translate (dry-run)

### Windows CMD
```bat
python -m silhouette_core.cli fhir translate --in "tests\data\hl7\adt_a01.hl7" --map "maps\adt_uscore.yaml" --bundle transaction --out out --dry-run
python -m silhouette_core.cli fhir translate --in "tests\data\hl7\oru_r01.hl7" --map "maps\oru_uscore.yaml" --bundle transaction --out out --dry-run
```

### PowerShell
```powershell
python -m silhouette_core.cli fhir translate `
  --in "tests\data\hl7\adt_a01.hl7" `
  --map "maps\adt_uscore.yaml" `
  --bundle transaction `
  --out out `
  --dry-run
```

### Bash
```bash
python -m silhouette_core.cli fhir translate \
  --in tests/data/hl7/adt_a01.hl7 \
  --map maps/adt_uscore.yaml \
  --bundle transaction \
  --out out \
  --dry-run
```

## Validate

### Local shape check
```bat
python -m silhouette_core.cli fhir validate --in "out/fhir/ndjson/Patient.ndjson"
```

### HAPI validator
```bat
java -jar validators\validator_cli.jar -version 4.0.1 -ig hl7.fhir.us.core#6.1.0 out\fhir\bundles\adt_a01.json
```

Use `--partner <name>` to apply `config/partners/<name>.yaml`.

## Post to a sandbox with server-side `$validate`
```bat
set FHIR_BASE=https://<your-sandbox>/fhir
set FHIR_TOKEN=<token>
python -m silhouette_core.cli fhir translate --in "tests\data\hl7\adt_a01.hl7" --map "maps\adt_uscore.yaml" --bundle transaction --out out --server "%FHIR_BASE%" --token "%FHIR_TOKEN%" --validate
```

Artifacts appear under `out/`:

- NDJSON resources in `out/fhir/ndjson/`
- Bundles in `out/fhir/bundles/`
- Metrics at `out/metrics.csv`
- Logs (`out/log.jsonl`) and dead letters (`out/deadletter/`)

## Flags

### `fhir translate`

| Flag | Default | Description |
| --- | --- | --- |
| `--in` | required | HL7 v2 file, directory, or glob |
| `--rules` | – | Validation profile YAML |
| `--map` | – | Mapping profile YAML |
| `--bundle` | `transaction` | Bundle type (`transaction` or `collection`) |
| `--out` | `out/` | Output directory |
| `--server` | – | FHIR server base URL |
| `--token` | – | Auth token for FHIR server |
| `--validate` | off | Validate output resources |
| `--dry-run` | off | Run without posting to server |
| `--message-mode` | off | Emit message bundles with MessageHeader (preview) |
| `--partner` | – | Partner config to apply |

### `fhir validate`

| Flag | Default | Description |
| --- | --- | --- |
| `--in` | required | NDJSON file(s) to validate |
| `--hapi` | off | Also run HAPI FHIR validator |
| `--partner` | – | Partner config to apply |
