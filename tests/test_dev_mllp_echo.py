from __future__ import annotations

import socket
import threading
import time

import scripts.dev_mllp_echo as echo

VT = b"\x0b"
FS = b"\x1c"
CR = b"\x0d"


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _wrap(msg: str) -> bytes:
    return VT + msg.encode("utf-8") + FS + CR


def test_dev_mllp_echo_ack_roundtrip():
    host = "127.0.0.1"
    port = _free_port()
    t = threading.Thread(target=echo.serve, args=(host, port), daemon=True)
    t.start()
    time.sleep(0.15)

    msg_id = "MSG-UNITTEST-123"
    hl7 = (
        f"MSH|^~\\&|SIL|HOSP|REC|HUB|202501010000||ADT^A01|{msg_id}|P|2.4\r\n"
        "PID|1||12345^^^HOSP^MR||DOE^JOHN\r\n"
    )
    with socket.create_connection((host, port), timeout=2.0) as s:
        s.sendall(_wrap(hl7))
        chunks = []
        s.settimeout(2.0)
        while True:
            b = s.recv(4096)
            if not b:
                break
            chunks.append(b)
            if FS in b:
                break

    ack_bytes = b"".join(chunks)
    assert ack_bytes.startswith(VT) and ack_bytes.endswith(FS + CR)
    ack_txt = ack_bytes[1:-2].decode("utf-8", "ignore")
    assert "MSA|AA|" + msg_id in ack_txt

