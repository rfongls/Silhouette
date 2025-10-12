#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Start Menu installer for Silhouette (no PowerShell).
- Creates .lnk shortcuts via a transient VBScript + cscript.exe
- Optionally creates .url web links
- No external Python packages required

Usage (per-user, no admin):
  python scripts/install_shortcuts.py

Custom path (system-wide requires admin usually):
  python scripts/install_shortcuts.py --start-menu-path "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\Silhouette"

See: python scripts/install_shortcuts.py --help
"""
import argparse
import os
import pathlib
import subprocess
import sys
import tempfile

APP_NAME = "Silhouette"
FOLDER_NAME = "Silhouette"   # Start Menu subfolder
DEFAULT_PORT = 8000          # change if your app runs elsewhere

def default_start_menu_dir() -> pathlib.Path:
    # Per-user Start Menu
    p = os.environ.get("APPDATA") or ""
    return pathlib.Path(p) / r"Microsoft\\Windows\\Start Menu\\Programs" / FOLDER_NAME

def repo_root() -> pathlib.Path:
    # best effort: script location -> repo root
    return pathlib.Path(__file__).resolve().parents[1]

def run_ui_bat_default(root: pathlib.Path) -> pathlib.Path:
    # Assuming scripts lives at repo/scripts, classic batch is at repo/run.ui.bat
    return root / "run.ui.bat"

def ensure_dir(path: pathlib.Path):
    path.mkdir(parents=True, exist_ok=True)

def write_url_shortcut(dest: pathlib.Path, url: str):
    """
    Writes a .url Internet Shortcut (works in Start menu).
    """
    content = f"[InternetShortcut]\nURL={url}\n"
    dest.write_text(content, encoding="utf-8")

def write_lnk_shortcut(dest: pathlib.Path, target: str, args: str = "", workdir: str = "", icon: str = ""):
    """
    Creates a .lnk via a short VBScript (no PowerShell, no pywin32).
    """
    vbs = f"""Set oWS = WScript.CreateObject("WScript.Shell")
Set lnk = oWS.CreateShortcut(\"{dest.as_posix()}\")
lnk.TargetPath = \"{target}\"
lnk.Arguments   = \"{args}\"
lnk.WorkingDirectory = \"{workdir}\"
"""
    if icon:
        vbs += f'lnk.IconLocation = "{icon}"\n'
    vbs += "lnk.Save\n"
    with tempfile.NamedTemporaryFile(prefix="mklnk_", suffix=".vbs", delete=False) as tf:
        tf.write(vbs.encode("utf-8"))
        temp_vbs = tf.name
    try:
        # Use cscript (console host) to avoid popping a window
        subprocess.run(
            ["cscript.exe", "//nologo", temp_vbs],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    finally:
        try:
            os.remove(temp_vbs)
        except OSError:
            pass

def has_write_access(path: pathlib.Path) -> bool:
    try:
        ensure_dir(path)
        test = path / ".perm.test"
        test.write_text("ok", encoding="utf-8")
        test.unlink(missing_ok=True)
        return True
    except Exception:
        return False

def parse_args():
    ap = argparse.ArgumentParser(description="Install Start Menu shortcuts for Silhouette without PowerShell.")
    ap.add_argument("--start-menu-path", default=None,
                    help="Custom Start Menu folder (default: per-user Start Menu).")
    ap.add_argument("--name-prefix", default=APP_NAME, help="Shortcut name prefix (default: Silhouette).")
    ap.add_argument("--classic-bat", default=None,
                    help="Path to run.ui.bat (default: auto-detected at repo root).")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT,
                    help=f"HTTP port for web shortcuts (default: {DEFAULT_PORT}).")
    ap.add_argument("--skip-url", action="store_true", help="Skip creating .url web links.")
    ap.add_argument("--dry-run", action="store_true", help="Print what would happen, do not write files.")
    return ap.parse_args()

def main():
    args = parse_args()
    root = repo_root()
    start_menu = pathlib.Path(args.start_menu_path) if args.start_menu_path else default_start_menu_dir()

    if not has_write_access(start_menu):
        print(f"[!] No write access to Start Menu path:\n    {start_menu}", file=sys.stderr)
        print("    Try running as admin, or use --start-menu-path to a per-user folder.", file=sys.stderr)
        sys.exit(1)

    ensure_dir(start_menu)

    # Resolve targets
    classic_bat = pathlib.Path(args.classic_bat) if args.classic_bat else run_ui_bat_default(root)
    if not classic_bat.exists():
        print(f"[!] Could not find run.ui.bat at:\n    {classic_bat}\n"
              f"    Use --classic-bat to specify the path.", file=sys.stderr)

    # Shortcuts to create
    # 1) Classic UI (batch) -> runs your current UI launcher
    classic_name = f"{args.name_prefix} (Classic UI).lnk"
    classic_dest = start_menu / classic_name

    # 2) Dev API server (Optional) -> uvicorn main:app --reload
    #    Only add if main.py exists.
    dev_name = f"{args.name_prefix} Dev API (Uvicorn).lnk"
    dev_dest = start_menu / dev_name
    main_py = root / "main.py"

    # 3) Landing web link (if you have /ui/landing) and Docs link
    landing_url = f"http://127.0.0.1:{args.port}/ui/landing"
    docs_url = f"http://127.0.0.1:{args.port}/docs/v2/README-agent.html"  # adjust if docs served differently

    # Show plan
    print(f"Installing Start Menu shortcuts to:\n  {start_menu}\n")

    # Create Classic UI link
    if classic_bat.exists():
        print(f" [+] {classic_dest.name} -> {classic_bat}")
        if not args.dry_run:
            write_lnk_shortcut(
                dest=classic_dest,
                target=str(classic_bat.resolve()),
                args="",
                workdir=str(root),
                icon=str(classic_bat.resolve()),  # you can point to an .ico later
            )
    else:
        print(" [!] Skipping Classic UI link (run.ui.bat not found).")

    # Create Dev server link (optional)
    if main_py.exists():
        # We invoke via cmd.exe /c so the working directory is correct and PATH resolves python env
        # If you prefer a venv python, update the `target` to that interpreter.
        cmd = r"%ComSpec%"
        args_line = f'/c python -m uvicorn main:app --reload --host 127.0.0.1 --port {args.port}'
        print(f" [+] {dev_dest.name} -> {cmd} {args_line}")
        if not args.dry_run:
            write_lnk_shortcut(
                dest=dev_dest,
                target=cmd,
                args=args_line,
                workdir=str(root),
                icon=str(main_py.resolve()),
            )
    else:
        print(" [!] Skipping Dev API link (main.py not found).")

    # .url links (optional)
    if not args.skip_url:
        landing_dest = start_menu / f"{args.name_prefix} Landing.url"
        docs_dest = start_menu / f"{args.name_prefix} Agent README.url"
        print(f" [+] {landing_dest.name} -> {landing_url}")
        print(f" [+] {docs_dest.name} -> {docs_url}")
        if not args.dry_run:
            write_url_shortcut(landing_dest, landing_url)
            write_url_shortcut(docs_dest, docs_url)

    print("\nDone.")
    if classic_bat.exists():
        print("Tip: Start the classic UI first time with the 'Classic UI' shortcut,")
        print("     then use the Landing link once the server is running on the chosen port.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
