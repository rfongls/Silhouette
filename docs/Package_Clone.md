# Build Deployable Clone (`silhouette_core/package_clone.py`)

## Purpose
Create a ZIP archive with core runtime files, a profile, and optional distillate for deployment.

## Usage
```bash
python -m silhouette_core.package_clone --profile silhouette_profile.json \
    --distillate distillate.json --version 1 --output-dir dist
```
This produces `silhouette_clone_v1.zip` under `dist/` containing selected core modules and `silhouette_profile.json`.
