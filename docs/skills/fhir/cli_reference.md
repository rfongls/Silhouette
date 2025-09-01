# FHIR CLI Reference

## `fhir translate`

| Flag | Type | Default | Required | Description | Example |
| --- | --- | --- | --- | --- | --- |
| `--in` | path | — | yes | HL7 v2 file, directory, or glob | `--in tests/data/hl7/adt_a01.hl7` |
| `--rules` | path | — | no | Validation profile YAML | `--rules tests/hl7/rules/rules.yaml` |
| `--map` | path | — | no | Mapping profile YAML | `--map maps/adt_uscore.yaml` |
| `--bundle` | choice | `transaction` | no | Bundle type | `--bundle collection` |
| `--out` | path | `out/` | no | Output directory | `--out out` |
| `--server` | URL | — | no | FHIR server base URL | `--server https://example.com/fhir` |
| `--token` | string | — | no | Auth token for FHIR server | `--token %FHIR_TOKEN%` |
| `--validate` | flag | false | no | Validate output resources | `--validate` |
| `--dry-run` | flag | false | no | Run without posting to server | `--dry-run` |
| `--message-mode` | flag | false | no | Emit message bundles with MessageHeader (preview) | `--message-mode` |
| `--partner` | string | — | no | Partner config to apply | `--partner example` |

### Examples

**Windows CMD**
```bat
python -m silhouette_core.cli fhir translate --in "tests\data\hl7\adt_a01.hl7" --map "maps\adt_uscore.yaml" --bundle transaction --out out --dry-run
```

**PowerShell**
```powershell
python -m silhouette_core.cli fhir translate `
  --in "tests\data\hl7\adt_a01.hl7" `
  --map "maps\adt_uscore.yaml" `
  --bundle transaction `
  --out out `
  --dry-run
```

**Bash**
```bash
python -m silhouette_core.cli fhir translate \
  --in tests/data/hl7/adt_a01.hl7 \
  --map maps/adt_uscore.yaml \
  --bundle transaction \
  --out out \
  --dry-run
```

## `fhir validate`

| Flag | Type | Default | Required | Description | Example |
| --- | --- | --- | --- | --- | --- |
| `--in` | glob | — | yes | NDJSON file(s) to validate | `--in out/fhir/ndjson/Patient.ndjson` |
| `--hapi` | flag | false | no | Also run HAPI FHIR validator | `--hapi` |
| `--partner` | string | — | no | Partner config to apply | `--partner example` |

### Examples

**Windows CMD**
```bat
python -m silhouette_core.cli fhir validate --in "out\fhir\ndjson\Patient.ndjson" --hapi
```

**PowerShell**
```powershell
python -m silhouette_core.cli fhir validate `
  --in "out\fhir\ndjson\Patient.ndjson" `
  --hapi
```

**Bash**
```bash
python -m silhouette_core.cli fhir validate \
  --in out/fhir/ndjson/Patient.ndjson \
  --hapi
```
