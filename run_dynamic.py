"""Development launcher that automatically selects a free port for Uvicorn."""
from __future__ import annotations

import argparse
import os
import socket
import sys
from contextlib import closing
from pathlib import Path
from typing import Iterable, Tuple


def _parse_range(spec: str) -> Tuple[int, int]:
    try:
        start_str, end_str = (spec or "").split("-", 1)
        start = int(start_str)
        end = int(end_str)
    except Exception:
        return (8000, 8100)
    if start > end:
        start, end = end, start
    return (start, end)


def is_free_port(port: int, host: str = "127.0.0.1") -> bool:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def pick_port(preferred: Iterable[int], scan_range: Tuple[int, int], host: str) -> int:
    preferred_tuple = tuple(preferred)
    for candidate in preferred_tuple:
        if candidate is None:
            continue
        if is_free_port(candidate, host):
            return candidate
    start, end = scan_range
    for candidate in range(start, end + 1):
        if candidate in preferred_tuple:
            continue
        if is_free_port(candidate, host):
            return candidate
    raise RuntimeError(
        f"No free port available in preferred set or range {start}-{end}."
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Launch the Silhouette app with automatic port selection."
    )
    parser.add_argument("--app", default="server:app", help="ASGI app path (module:app)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--reload",
        dest="reload",
        action="store_true",
        default=True,
        help="Enable auto-reload (default)",
    )
    parser.add_argument(
        "--no-reload",
        dest="reload",
        action="store_false",
        help="Disable auto-reload",
    )
    parser.add_argument(
        "--range",
        dest="scan",
        default="8000-8100",
        help="Fallback port scan range start-end",
    )
    args = parser.parse_args(argv)

    host = os.getenv("SILHOUETTE_HOST", args.host)

    preferred: list[int] = []
    env_port = os.getenv("SILHOUETTE_PORT")
    if env_port:
        try:
            preferred.append(int(env_port))
        except ValueError:
            pass
    if args.port not in preferred:
        preferred.append(args.port)
    for alt in (8010, 8020):
        if alt not in preferred:
            preferred.append(alt)

    scan_spec = os.getenv("SILHOUETTE_PORT_RANGE", args.scan)
    scan_range = _parse_range(scan_spec)

    try:
        port = pick_port(preferred, scan_range, host)
    except RuntimeError as exc:
        print(f"[silhouette] {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    Path(".silhouette_port").write_text(str(port), encoding="utf-8")
    print(
        f"[silhouette] Starting {args.app} on http://{host}:{port} (auto-selected)",
        flush=True,
    )

    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover - convenience message
        print("uvicorn is required to run the development server.", file=sys.stderr)
        raise SystemExit(1) from exc

    uvicorn.run(args.app, host=host, port=port, reload=args.reload)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
