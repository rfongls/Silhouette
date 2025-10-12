#!/usr/bin/env python3
"""Install Windows Start Menu shortcuts for Silhouette (pure Python)."""
from __future__ import annotations

import argparse
import ctypes
import os
from ctypes import wintypes
from pathlib import Path


APP_NAME = "Silhouette"
DEFAULT_BAT = "run.ui.bat"
DEFAULT_ICON = "static\\favicon.ico"
DEFAULT_URL = "http://localhost:8000/ui/landing"


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


def _create_url_shortcut(destination: Path, url: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(f"[InternetShortcut]\nURL={url}\n", encoding="utf-8")


# --- Minimal COM helpers ----------------------------------------------------

ole32 = ctypes.OleDLL("ole32")


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


CLSCTX_INPROC_SERVER = 0x1


def _guid(text: str) -> GUID:
    guid = GUID()
    hr = ole32.CLSIDFromString(wintypes.LPCWSTR(text), ctypes.byref(guid))
    if hr != 0:
        raise OSError(f"CLSIDFromString failed for {text}: 0x{hr:08x}")
    return guid


CLSID_SHELL_LINK = _guid("{00021401-0000-0000-C000-000000000046}")
IID_ISHELLLINKW = _guid("{000214F9-0000-0000-C000-000000000046}")
IID_IPERSISTFILE = _guid("{0000010b-0000-0000-C000-000000000046}")


def _method(ptr: ctypes.c_void_p, index: int, restype, *argtypes):
    if not ptr:
        raise ValueError("COM pointer is null")
    vtbl = ctypes.cast(ptr.value, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    func_type = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
    func = func_type(vtbl[index])

    def call(*args):
        return func(ptr, *args)

    return call


def create_shortcut(path: Path, target: Path, workdir: Path, *, icon: Path | None, args: str | None, description: str | None) -> None:
    hr_init = ole32.CoInitialize(None)
    coinit_ok = hr_init in (0, 0x00000001)  # S_OK or S_FALSE
    if not coinit_ok:
        raise OSError(f"CoInitialize failed: 0x{hr_init:08x}")
    try:
        shell_link = ctypes.c_void_p()
        hr = ole32.CoCreateInstance(
            ctypes.byref(CLSID_SHELL_LINK),
            None,
            CLSCTX_INPROC_SERVER,
            ctypes.byref(IID_ISHELLLINKW),
            ctypes.byref(shell_link),
        )
        if hr != 0:
            raise OSError(f"CoCreateInstance failed: 0x{hr:08x}")

        QueryInterface = _method(shell_link, 0, wintypes.HRESULT, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p))
        Release = _method(shell_link, 2, ctypes.c_ulong)
        SetDescription = _method(shell_link, 7, wintypes.HRESULT, wintypes.LPCWSTR)
        SetWorkingDirectory = _method(shell_link, 9, wintypes.HRESULT, wintypes.LPCWSTR)
        SetArguments = _method(shell_link, 11, wintypes.HRESULT, wintypes.LPCWSTR)
        SetIconLocation = _method(shell_link, 17, wintypes.HRESULT, wintypes.LPCWSTR, ctypes.c_int)
        SetPath = _method(shell_link, 20, wintypes.HRESULT, wintypes.LPCWSTR)

        persist = ctypes.c_void_p()
        hr = QueryInterface(ctypes.byref(IID_IPERSISTFILE), ctypes.byref(persist))
        if hr != 0:
            Release()
            raise OSError(f"QueryInterface(IPersistFile) failed: 0x{hr:08x}")

        PersistRelease = None
        try:
            Save = _method(persist, 6, wintypes.HRESULT, wintypes.LPCWSTR, wintypes.BOOL)
            PersistRelease = _method(persist, 2, ctypes.c_ulong)

            hr = SetPath(wintypes.LPCWSTR(str(target)))
            if hr != 0:
                raise OSError(f"SetPath failed: 0x{hr:08x}")
            hr = SetWorkingDirectory(wintypes.LPCWSTR(str(workdir)))
            if hr != 0:
                raise OSError(f"SetWorkingDirectory failed: 0x{hr:08x}")
            if description:
                hr = SetDescription(wintypes.LPCWSTR(description))
                if hr != 0:
                    raise OSError(f"SetDescription failed: 0x{hr:08x}")
            if args:
                hr = SetArguments(wintypes.LPCWSTR(args))
                if hr != 0:
                    raise OSError(f"SetArguments failed: 0x{hr:08x}")
            if icon and icon.exists():
                hr = SetIconLocation(wintypes.LPCWSTR(str(icon)), ctypes.c_int(0))
                if hr != 0:
                    raise OSError(f"SetIconLocation failed: 0x{hr:08x}")

            hr = Save(wintypes.LPCWSTR(str(path)), wintypes.BOOL(True))
            if hr != 0:
                raise OSError(f"Save failed: 0x{hr:08x}")
        finally:
            if PersistRelease is not None:
                PersistRelease()
        Release()
    finally:
        if coinit_ok:
            ole32.CoUninitialize()


def run_install(repo_root: Path, *, all_users: bool, label: str, bat_rel: str, icon_rel: str | None, landing_url: str | None) -> None:
    shortcuts_dir = start_menu_dir(all_users)
    shortcuts_dir.mkdir(parents=True, exist_ok=True)

    target = (repo_root / bat_rel).resolve()
    if not target.exists():
        raise FileNotFoundError(f"Launcher batch not found: {target}")

    icon_path = (repo_root / icon_rel).resolve() if icon_rel else None

    shortcut_path = shortcuts_dir / f"{label}.lnk"
    create_shortcut(
        shortcut_path,
        target,
        repo_root,
        icon=icon_path if icon_path and icon_path.exists() else None,
        args=None,
        description="Launch Silhouette UI",
    )

    if landing_url:
        _create_url_shortcut(shortcuts_dir / f"{label} – Open in Browser.url", landing_url)

    print(f"[OK] Start Menu shortcuts installed at {shortcuts_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Install Windows Start Menu shortcuts for Silhouette")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--all-users", action="store_true", help="Install for all users (requires admin)")
    scope.add_argument("--user", action="store_true", help="Install for current user (default)")
    parser.add_argument("--repo-root", default=".", help="Repository root where run.ui.bat lives")
    parser.add_argument("--label", default=APP_NAME, help="Shortcut label (default: Silhouette)")
    parser.add_argument("--target-bat", default=DEFAULT_BAT, help="Relative path to run.ui.bat")
    parser.add_argument("--icon", default=DEFAULT_ICON, help="Relative path to .ico (optional)")
    parser.add_argument("--landing", default=DEFAULT_URL, help="Landing page URL (blank to skip)")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    landing = args.landing.strip() if args.landing else ""

    run_install(
        repo_root,
        all_users=bool(args.all_users),
        label=args.label.strip() or APP_NAME,
        bat_rel=args.target_bat,
        icon_rel=args.icon if args.icon else None,
        landing_url=landing or None,
    )


if __name__ == "__main__":
    main()

