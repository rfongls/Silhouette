# Windows Start Menu shortcuts

Silhouette ships **pure-Python** helpers for installing, uninstalling, or
repairing Windows Start Menu shortcuts without PowerShell or external
dependencies.

## Scripts

All scripts live in `tools/`:

| Script | Purpose |
| --- | --- |
| `win_install.py` | Create shortcuts |
| `win_uninstall.py` | Remove shortcuts |
| `win_reset.py` | Uninstall then install (handy “repair”) |

## Usage

```bat
# per-user (default)
python tools\win_install.py --user
python tools\win_uninstall.py --user
python tools\win_reset.py --user

# all users (requires elevated prompt)
python tools\win_install.py --all-users
```

Shared flags:

- `--repo-root` (default `.`) – folder that contains `run.ui.bat`
- `--label` (default `Silhouette`) – Start Menu folder + shortcut prefix
- `--target-bat` (default `run.ui.bat`) – launcher batch invoked by the shortcut
- `--icon` (default `static\favicon.ico`) – optional `.ico`
- `--landing` (default `http://localhost:8000/ui/landing`) – creates a web link; pass
  an empty string to skip

## What gets created

- Start Menu folder:
  - Per-user: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Silhouette`
  - All users: `%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\Silhouette`
- `.lnk` shortcut pointing to `run.ui.bat`
- Optional `.url` shortcut “Silhouette – Open in Browser” → landing page

## Notes

- The installer uses only the Python standard library (`ctypes` COM bindings) to
  build a `.lnk` file.
- `win_reset.py` is idempotent; it removes the folder then re-runs the installer
  with the arguments you supply.
- The scripts make no other changes to the repository or environment.

