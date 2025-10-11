#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

DEFAULT_FOLDER = "Silhouette"


def start_menu_user() -> Path:
    base = os.environ.get("APPDATA", "")
    return Path(base) / r"Microsoft/Windows/Start Menu/Programs"


def start_menu_all_users() -> Path:
    base = os.environ.get("PROGRAMDATA", "")
    return Path(base) / r"Microsoft/Windows/Start Menu/Programs"


def inside(parent: Path, child: Path) -> bool:
    try:
        return child.resolve().is_relative_to(parent.resolve())
    except AttributeError:
        parent_r = parent.resolve()
        child_r = child.resolve()
        return str(child_r).startswith(str(parent_r))


def rm_tree(target: Path, *, dry: bool, verbose: bool) -> None:
    if dry or verbose:
        print(f"[uninstall] remove folder: {target}")
    if not dry and target.exists():
        shutil.rmtree(target, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remove Silhouette Start Menu shortcuts (no PowerShell)."
    )
    parser.add_argument(
        "--folder-name",
        default=DEFAULT_FOLDER,
        help="Start Menu folder name (default: Silhouette)",
    )
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument(
        "--only-user",
        action="store_true",
        help="Remove in current user's Start Menu only",
    )
    scope.add_argument(
        "--all-users",
        action="store_true",
        help="Remove in All Users (ProgramData) Start Menu only",
    )
    parser.add_argument(
        "--both",
        action="store_true",
        help="Remove in both user and all-users Start Menus",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be removed")
    parser.add_argument("--verbose", action="store_true", help="Print paths and actions")
    args = parser.parse_args()

    targets: list[Path] = []
    if args.only_user:
        targets.append(start_menu_user() / args.folder_name)
    elif args.all_users:
        targets.append(start_menu_all_users() / args.folder_name)
    else:
        targets.append(start_menu_user() / args.folder_name)
        if args.both:
            targets.append(start_menu_all_users() / args.folder_name)

    safe_roots = [start_menu_user(), start_menu_all_users()]
    for target in targets:
        if not any(inside(root, target) for root in safe_roots):
            print(f"[uninstall] REFUSING to touch: {target} (outside Start Menu roots)")
            continue
        rm_tree(target, dry=args.dry_run, verbose=args.verbose)

    if args.dry_run:
        print("[uninstall] dry-run complete; nothing was deleted.")
    else:
        print("[uninstall] done.")


if __name__ == "__main__":
    main()
