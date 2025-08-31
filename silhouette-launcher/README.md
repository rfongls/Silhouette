# Silhouette Launcher (Portable GUI)

Pick a Silhouette repo folder, choose a skill (e.g., `fhir`), click **Run Setup**.
Creates `.venv` in that repo, installs `-e .[<skill>]`, runs smoke checks,
and optionally starts a local **HAPI FHIR** (Docker) on port 8080.

## Run from source
```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate && pip install -r requirements.txt && python -m launcher.main
# macOS/Linux
source .venv/bin/activate && pip install -r requirements.txt && python -m launcher.main
```

## CLI fallback (headless)

Run without PySide6 (e.g., on servers or behind proxies):

```bash
python -m launcher.main --cli --repo C:\path\to\Silhouette --skill fhir --with-hapi
```

## Build a single EXE (Windows)

```bat
build_windows.bat
```

## Skills supported

`core, runtime, ml, dev, eval, validate, fhir, all`

