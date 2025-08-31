# Agent Setup

Silhouette provides one-click scripts for all platforms.

## One-click usage

| OS | Command |
|---|---|
| Windows | Double-click `setup.bat` |
| macOS | Double-click `setup.command` |
| Linux/macOS terminal | `./setup.sh` |

Run the script and follow the prompts. It creates `.venv`, installs the selected skill extras, and performs smoke checks. Windows users can instead double-click `setup.ps1` from PowerShell.

## Non-interactive

```bash
python setup.py --skill fhir --with-hapi --yes
```

## Skills ↔ extras

| Skill | Extras |
|-------|--------|
| core | *(none)* |
| runtime | `[runtime]` |
| ml | `[ml]` |
| dev | `[dev]` |
| eval | `[eval]` |
| validate | `[validate]` |
| fhir | `[fhir]` |
| all | `[runtime,ml,dev,eval,validate,fhir]` |

## Windows Launcher

An optional Windows Launcher executable provides a GUI wrapper around this setup and can bootstrap any skill.

## Troubleshooting

- **Proxy/offline**: set `PIP_INDEX_URL` or use offline wheels.
- **HAPI**: requires Docker; pass `--with-hapi` to start a local server.
- **Reruns**: safe to re-run; existing `.venv` will be reused.

## After setup

Activate the virtualenv and run the CLI:

```bash
# macOS/Linux
source .venv/bin/activate && silhouette --version

# Windows
.\.venv\Scripts\activate && silhouette --version
```
