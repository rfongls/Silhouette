# Repo Integration

This document outlines the repository integration components for Silhouette Core.

## Components

- **Local & Git Adapters** – read-only access to repositories.
- **Repo Map** – generates an enriched JSON map of repository files and languages.
- **Run Artifacts** – records command invocations for reproducibility.
- **Local CI** – lightweight script to run lint, type-checking, tests, and security tools offline.
- **Policy & Secret Scanner** – YAML policy gates and a regex/entropy-based scanner.

## Quickstart

```bash
silhouette repo map . --json-out artifacts/repo_map.json --compute-hashes
bash scripts/ci_local.sh
bash scripts/repro.sh artifacts/<timestamp>/silhouette_run.json
```

## Sparse Checkout

Use glob patterns to include/exclude files, e.g. `**/*.py` or `!**/node_modules/**`.

## Posture

All operations run in read-only mode by default. Advanced write/PR features will
be enabled in future releases.
