# Release Playbook

Milestone reference: [docs/Phase_10_Completion.md](docs/Phase_10_Completion.md)

## Pre-flight
- Ensure `main` branch is green (CI + regression gates).
- Run final selfcheck:
  ```bash
  silhouette selfcheck --policy profiles/core/policy.yaml
  ```
- Run regression gates:
  ```bash
  make gates
  ```

## Versioning

* Bump version in `pyproject.toml` and `silhouette_core/__init__.py`.
* Commit with `chore(release): vX.Y.Z`.
* Tag: `git tag vX.Y.Z && git push origin vX.Y.Z`.

## Build

```bash
make clean
make build
```

Outputs: `dist/*.whl` and `dist/*.tar.gz`.

## Artifacts to Attach

* `dist/*.whl`, `dist/*.tar.gz` (installable packages).
* `artifacts/scoreboard/index.html` (latest snapshot).
* `artifacts/scoreboard/history.html` (full history).
* `artifacts/scoreboard/latest.json` (machine-readable snapshot).
* `artifacts/gates/gate_summary.json` (regression gate summary).
* `WATERMARK.json` (provenance marker).
* `COMPLIANCE.md` (scanner rules).
* `CUSTOMER_LICENSE_TEMPLATE.md` (customer license contract).

## GitHub Release

* Create release `vX.Y.Z`.
* Attach all above artifacts.
* Paste changelog section from `CHANGELOG.md`.

## Post-release

* Verify wheel install:
  ```bash
  pip install dist/*.whl
  silhouette run --offline
  ```
* Announce internal availability.

