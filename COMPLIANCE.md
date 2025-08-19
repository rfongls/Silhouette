# Compliance Guide

This project includes basic scanning and redaction utilities to help catch common
issues before artifacts are published.

## Licensing

- Silhouette Core is proprietary.
- Training, redistribution, or fine-tuning without contract is prohibited.
- Customer licenses are issued via `scripts/issue_customer_license.py`.
- Each issued license embeds a `customer_id` into WATERMARK.json for provenance.
- License artifacts are stored in `artifacts/licenses/`.

## Security Scanner
Run the repository scanner to detect secrets, PII, and license violations:

```bash
python -m security.scanner --path . \
  --license_whitelist MIT,Apache-2.0,BSD-2-Clause,BSD-3-Clause \
  --license_denylist GPL-3.0,AGPL-3.0,MPL-2.0 \
  --max_high 0 --max_medium 10 --max_low 999
```

## Watermarks
All release artifacts include `WATERMARK.json` with the git commit hash, artifact
SHA256, license tag, optional customer ID, and provenance metadata. Do not remove
or modify watermarks. Verify with:

```bash
python scripts/verify_watermark.py --artifact_dir models/student-core-kd
```
