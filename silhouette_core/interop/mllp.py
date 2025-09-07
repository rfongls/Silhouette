from __future__ import annotations

import socket
from typing import List

VT = b"\x0b"
FS = b"\x1c"
CR = b"\x0d"


def _wrap_hl7(msg: str) -> bytes:
    return VT + msg.encode("utf-8") + FS + CR


def send_mllp_batch(host: str, port: int, messages: List[str], timeout: float = 5.0):
    acks: list[str] = []
    with socket.create_connection((host, port), timeout=timeout) as s:
        for m in messages:
            s.sendall(_wrap_hl7(m))
            chunks: list[bytes] = []
            while True:
                b = s.recv(4096)
                if not b:
                    break
                chunks.append(b)
                if FS in b:
                    break
            acks.append(b"".join(chunks).decode("utf-8", "ignore"))
    return acks
