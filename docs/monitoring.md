# Self-Reflective Monitoring

Silhouette can monitor its own behavior and memory for drift or persona violations.
Use the commands below to generate various reports.

## Commands
- `:drift-report` – compare recent memory to historical baseline using `config/drift.yml`.
- `:summary` – generate a short summary of the latest session log in `reports/`.
- `:persona-audit` – check memory entries against persona rules.
- `:selfcheck --full` – run all of the above and standard checks together.
- `:export-profile` – generate a portable agent profile.
- `python -m silhouette_core.distiller` – produce a compact knowledge distillate.
- `python -m silhouette_core.package_clone` – build `silhouette_clone_vX.zip`.
- `:agent deploy <target>` – deploy a clone archive to a host path or `ssh://` URL.
- `python -m silhouette_core.quantize_models` – convert embeddings for edge runtime.
