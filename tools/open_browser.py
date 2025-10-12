from __future__ import annotations

import os
import socket
import sys
import time
import urllib.request
import webbrowser


def _wait_for_port(host: str, port: int, timeout_s: int = 90) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.5):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def _wait_for_http(url: str, timeout_s: int = 30) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if 200 <= getattr(resp, "status", 0) < 500:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def main() -> None:
    url = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.getenv("SIL_OPENURL", "http://127.0.0.1:8000/ui/landing")
    )
    host = "127.0.0.1"
    port = 8000

    temp_dir = os.getenv("TEMP") or os.getenv("TMP") or "."
    flag_path = os.path.join(temp_dir, "silhouette_browser_opened.flag")
    if os.path.exists(flag_path):
        return

    if _wait_for_port(host, port, 90):
        if not _wait_for_http("http://127.0.0.1:8000/ping", 15):
            _wait_for_http(url, 15)
        try:
            webbrowser.open(url, new=1, autoraise=True)
            with open(flag_path, "w", encoding="utf-8") as handle:
                handle.write("1")
        except Exception:
            pass


if __name__ == "__main__":
    main()
