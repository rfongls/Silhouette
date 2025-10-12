#!/usr/bin/env python3
"""Reset Windows Start Menu shortcuts for Silhouette (uninstall + install)."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset Silhouette Start Menu shortcuts")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--all-users", action="store_true", help="Reset for all users")
    scope.add_argument("--user", action="store_true", help="Reset for current user (default)")
    parser.add_argument("--repo-root", default=".", help="Repository root where run.ui.bat lives")
    parser.add_argument("--label", default="Silhouette", help="Shortcut label (default: Silhouette)")
    parser.add_argument("--target-bat", default="run.ui.bat", help="Relative path to run.ui.bat")
    parser.add_argument("--icon", default="static\\favicon.ico", help="Relative path to .ico (optional)")
    parser.add_argument("--landing", default="http://localhost:8000/ui/landing", help="Landing page URL (blank to skip)")
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    python = sys.executable
    scope_flag = "--all-users" if args.all_users else "--user"

    uninstall_cmd = [python, str(here / "win_uninstall.py"), scope_flag]
    install_cmd = [
        python,
        str(here / "win_install.py"),
        scope_flag,
        "--repo-root",
        str(Path(args.repo_root).resolve()),
        "--label",
        str(args.label),
        "--target-bat",
        str(args.target_bat),
        "--icon",
        str(args.icon),
    ]
    landing = args.landing.strip() if args.landing else ""
    install_cmd.extend(["--landing", landing])

    print("[1/2] Removing existing shortcuts …")
    subprocess.run(uninstall_cmd, check=True)

    print("[2/2] Installing shortcuts …")
    subprocess.run(install_cmd, check=True)

    print("[OK] Shortcuts reset")


if __name__ == "__main__":
    main()

