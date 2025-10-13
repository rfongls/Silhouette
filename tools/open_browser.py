from __future__ import annotations

import pathlib
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


def _wait_for_http(url: str, timeout_s: int = 15) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:  # noqa: S310 (local URL)
                if 200 <= response.status < 500:
                    return True
        except Exception:
            time.sleep(0.4)
    return False


def main() -> None:
    url = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/ui").strip()
    host = "127.0.0.1"
    port = 8000

    out_dir = pathlib.Path("out")
    out_dir.mkdir(parents=True, exist_ok=True)
    flag_path = out_dir / "ui_opened.flag"

    if flag_path.exists():
        return

    if _wait_for_port(host, port, 90):
        if not _wait_for_http("http://127.0.0.1:8000/ping", 15):
            _wait_for_http(url, 15)
        try:
            webbrowser.open(url, new=1, autoraise=True)
            flag_path.write_text("1", encoding="utf-8")
        except Exception:
            pass


if __name__ == "__main__":
    main()
