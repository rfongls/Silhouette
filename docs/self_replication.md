# Clone & Self-Replication

This guide walks through creating a portable Silhouette clone.

1. **Export the profile**
   ```bash
   python -m silhouette_core.profile_exporter
   ```
2. **Distill knowledge**
   ```bash
   python -m silhouette_core.distiller
   ```
3. **Quantize embeddings**
   ```bash
   python -m silhouette_core.quantize_models
   ```
4. **Package the clone**
   ```bash
   python -m silhouette_core.package_clone
   ```
5. **Deploy**
   ```bash
   :agent deploy /path/to/host
   ```
