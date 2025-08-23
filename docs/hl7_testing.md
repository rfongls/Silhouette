# HL7 Testing (v2.3–v2.8, Option B)

Silhouette’s HL7 tests run **with HL7apy’s installed dictionaries** and automatically skip versions that are not supported locally.

## How it works
- Default requested versions: `2.3, 2.4, 2.5, 2.5.1, 2.6, 2.7, 2.7.1, 2.8`.
- We intersect this list with `hl7apy.consts.SUPPORTED_VERSIONS` at runtime.
- Each test uses `@pytest.mark.hl7` and skips gracefully if a version isn't supported or raises `UnsupportedVersion`.

## Configure versions
Use an env var to narrow or expand versions:
```bash
# run only two versions
SILHOUETTE_HL7_VERSIONS="2.5.1,2.7" pytest -q

# try all dictionaries hl7apy ships
SILHOUETTE_HL7_VERSIONS="ALL" pytest -q
```

## CI

`./scripts/ci_local.sh` runs:

* `ruff check silhouette_core tests`
* `pytest -q` (HL7 suite auto-skips unsupported versions)

