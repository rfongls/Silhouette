#!/usr/bin/env python3
"""
Dev MLLP Echo Server
--------------------
A tiny HL7 MLLP listener that ACKs each inbound message, echoing MSH-10 in MSA-2.
Useful for manual tests with /api/interop/mllp/send and for quick local pipelines.

Usage:
    python scripts/dev_mllp_echo.py --host 127.0.0.1 --port 2575

Notes:
- Frames are delimited by VT (0x0b) ... FS (0x1c) CR (0x0d).
- Multiple frames per TCP connection are supported.
"""
from __future__ import annotations

import argparse
import socket
import threading
from typing import Tuple

VT = b"\x0b"
FS = b"\x1c"
CR = b"\x0d"


def make_ack(inbound_frame: bytes) -> bytes:
    """Build a minimal ACK referencing inbound MSH-10 if present."""
    try:
        txt = inbound_frame.decode("utf-8", "ignore")
        msh = next((l for l in txt.splitlines() if l.startswith("MSH|")), None)
        msg_id = msh.split("|")[9] if msh else "NA"
    except Exception:
        msg_id = "NA"
    # Very minimal ACK — good enough for round-trip testing
    ack_txt = (
        "MSH|^~\\&|ECHO|MLLP||CLIENT|202501010000||ACK^A01|{mid}-ACK|P|2.4\r\n"
        "MSA|AA|{mid}\r\n"
    ).format(mid=msg_id)
    return VT + ack_txt.encode("utf-8") + FS + CR


def extract_frames(buffer: bytes) -> Tuple[list[bytes], bytes]:
    """
    Extract all available MLLP frames from the buffer.
    Returns (frames, remainder).
    """
    frames: list[bytes] = []
    i = 0
    while True:
        start = buffer.find(VT, i)
        if start == -1:
            # No start byte found; keep remainder
            return frames, buffer[i:] if i else buffer
        end = buffer.find(FS, start + 1)
        if end == -1:
            # No end yet; keep from start of current frame
            return frames, buffer[start:]
        # Frame is VT..FS (exclusive); there may be a trailing CR after FS
        frame = buffer[start + 1 : end]
        remainder = buffer[end + 1 :]
        if remainder[:1] == CR:
            remainder = remainder[1:]
        frames.append(frame)
        # Continue scanning the remainder for additional frames
        buffer = remainder
        i = 0


def handle_conn(conn: socket.socket, addr: Tuple[str, int]) -> None:
    peer = f"{addr[0]}:{addr[1]}"
    try:
        with conn:
            buf = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    # EOF / peer closed
                    break
                buf += chunk
                frames, buf = extract_frames(buf)
                for fr in frames:
                    conn.sendall(make_ack(fr))
    except Exception as e:
        print(f"[MLLP-ECHO] connection error from {peer}: {e}")


def serve(host: str, port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen(16)
        print(f"[MLLP-ECHO] Listening on {host}:{port}")
        while True:
            c, a = s.accept()
            t = threading.Thread(target=handle_conn, args=(c, a), daemon=True)
            t.start()


def main() -> None:
    ap = argparse.ArgumentParser(description="Dev MLLP echo server")
    ap.add_argument("--host", default="127.0.0.1", help="bind host (default: 127.0.0.1)")
    ap.add_argument("--port", type=int, default=2575, help="bind port (default: 2575)")
    args = ap.parse_args()
    serve(args.host, args.port)


if __name__ == "__main__":
    main()
