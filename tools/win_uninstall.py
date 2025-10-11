#!/usr/bin/env python3
"""Remove Windows Start Menu shortcuts for Silhouette."""
from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path


APP_NAME = "Silhouette"


def start_menu_dir(all_users: bool) -> Path:
    if all_users:
        base = os.environ.get("PROGRAMDATA")
        if not base:
            raise RuntimeError("PROGRAMDATA is not set; cannot locate all-users Start Menu.")
        root = Path(base) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    else:
        base = os.environ.get("APPDATA")
        if not base:
            raise RuntimeError("APPDATA is not set; cannot locate user Start Menu.")
        root = Path(base) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    return root / APP_NAME


def remove_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Uninstall Silhouette Start Menu shortcuts")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--all-users", action="store_true", help="Remove shortcuts for all users")
    scope.add_argument("--user", action="store_true", help="Remove shortcuts for current user (default)")
    args = parser.parse_args()

    directory = start_menu_dir(all_users=bool(args.all_users))
    if directory.exists():
        remove_dir(directory)
        print(f"[OK] Removed {directory}")
    else:
        print(f"[OK] Nothing to remove (missing {directory})")


if __name__ == "__main__":
    main()

