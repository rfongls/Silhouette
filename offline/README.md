# Offline Bundle

This folder houses **all dependencies** needed to run the app **without internet**:

```
offline/
  wheels/                  # Python wheelhouse (pip installable offline)
  requirements.lock        # Pinned Python deps for offline install
  docker/
    IMAGES.txt             # List of Docker images used by skills
    *.tar                  # Saved Docker images (optional)
```

## 1) Build the wheelhouse (while online)

**Linux/macOS**
```bash
scripts/offline_build_wheels.sh
```

**Windows (CMD)**
```bat
scripts\offline_build_wheels.bat
```

This will:
- create `offline/wheels/`
- download all wheels pinned in `offline/requirements.lock`

## 2) Install dependencies offline

**Linux/macOS**
```bash
python -m venv .venv
. .venv/bin/activate
scripts/offline_install_wheels.sh
```

**Windows (CMD)**
```bat
python -m venv .venv
call .venv\Scripts\activate.bat
scripts\offline_install_wheels.bat
```

This will:
- use only `offline/wheels/` (no network)
- install packages pinned in `offline/requirements.lock`

## 3) Docker images (optional)

If you will use skills that call containerized tools, you can save/load images:

**Images used**: see `offline/docker/IMAGES.txt`

**Save (online)**:
```bash
scripts/offline_save_docker.sh
```

**Load (offline)**:
```bash
scripts/offline_load_docker.sh
```

> Requires Docker Engine. This step is optional if you only use offline stubs/wrappers that do not call Docker.

## 4) Seeds and Scope (already offline)

Cybersecurity skills use local seeds:
```
data/security/seeds/cve/cve_seed.json
data/security/seeds/kev/kev_seed.json
docs/cyber/scope_example.txt
```

You can generate these via CI or locally:
```bash
mkdir -p data/security/seeds/cve data/security/seeds/kev docs/cyber
echo '{ "CVE-0001": {"summary":"Demo CVE for offline tests","severity":5} }' > data/security/seeds/cve/cve_seed.json
echo '{ "cves": ["CVE-0001"] }' > data/security/seeds/kev/kev_seed.json
printf 'example.com\n*.example.com\nsub.example.com\n' > docs/cyber/scope_example.txt
```

## 5) Notes
- Keep `offline/requirements.lock` minimal and pinned (only what you truly need).
- If you add new packages, regenerate the wheelhouse **before** going offline.
- You can create platform-specific subfolders (e.g., `offline/wheels-win/`) if needed.
