# Security

- License and secret scanner: `silhouette_core/security/scanner.py`
- Redaction utilities: `security/redaction.py`
- Watermark tooling: `scripts/watermark_artifact.py`, `scripts/verify_watermark.py`

## Scanner
```bash
python -m silhouette_core.security.scanner --path . --out artifacts/security_report.json \
    --license_whitelist MIT,Apache-2.0 --license_denylist GPL-3.0
```
Counts of low/medium/high findings are compared against thresholds `--max_low`, `--max_medium`, `--max_high`.

## Redaction
```python
from security.redaction import Redactor
redactor = Redactor()
print(redactor.redact_text("API key: AKIA..."))
```

## Watermark
```bash
python scripts/watermark_artifact.py --artifact_dir dist/model --customer_id 123
python scripts/verify_watermark.py --artifact_dir dist/model
```
