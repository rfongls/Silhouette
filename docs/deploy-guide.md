# Deploy Guide

To create a portable clone archive, run:

```
python -m silhouette_core.profile_exporter
python -m silhouette_core.distiller
python -m silhouette_core.package_clone --version 1
```

Copy `silhouette_clone_v1.zip` to your target host and deploy with:

```
:agent deploy <target>
```

`<target>` can be a local directory or `ssh://user@host`.
