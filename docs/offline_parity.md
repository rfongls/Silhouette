# Offline Parity

This guide demonstrates how to run core Silhouette workflow without any network
access. The flow mirrors the CI steps while relying solely on local assets.

## Prerequisites
- [Silhouette](../README.md) and its dependencies installed locally
- `ruff` for linting
- Optional: development container or local wheelhouse for reproducible installs
- Ability to temporarily disable network (airplane mode or firewall rules)

## Commands

```bash
export SILHOUETTE_OFFLINE=1
ruff check silhouette_core tests
bash scripts/offline_check.sh
```

## Expected Output
- `ruff check` completes with no errors
- `offline_check.sh` prints the path to artifacts under
  `artifacts/<YYYYMMDD_HHMMSS>/` containing:
  - `repo_map.json`
  - `hotpaths.json`
  - `suggest_tests.txt`
  - `ci_summary.json`

## Common Pitfalls
- Forgetting to set `SILHOUETTE_OFFLINE=1`
- Missing local wheels or tools; populate a wheelhouse before disconnecting
- Leaving a network connection enabled (test by disabling Wi-Fi or firewall)
