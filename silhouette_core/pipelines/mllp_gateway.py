"""Minimal MLLP server for HL7 v2 messages."""
from __future__ import annotations
import socket
import socketserver
from datetime import datetime
from pathlib import Path

START_BLOCK = b"\x0b"
END_BLOCK = b"\x1c"
CARRIAGE_RETURN = b"\x0d"


class MLLPHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        data = b""
        while True:
            chunk = self.request.recv(1024)
            if not chunk:
                break
            data += chunk
            if END_BLOCK in chunk:
                break
        message = data.strip(START_BLOCK + END_BLOCK + CARRIAGE_RETURN)
        out_dir = Path(self.server.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        (out_dir / f"{ts}.hl7").write_bytes(message + b"\r")
        ack = (
            START_BLOCK
            + b"MSH|^~\\&|SIL||ACK|"
            + CARRIAGE_RETURN
            + b"MSA|AA|"
            + CARRIAGE_RETURN
            + END_BLOCK
            + CARRIAGE_RETURN
        )
        self.request.sendall(ack)


class MLLPServer(socketserver.TCPServer):
    def __init__(self, server_address, handler, out_dir: str):
        super().__init__(server_address, handler)
        self.out_dir = out_dir


def run(host: str = "127.0.0.1", port: int = 2575, out_dir: str = "out/hl7") -> None:
    with MLLPServer((host, port), MLLPHandler, out_dir) as server:
        server.serve_forever()


def send(host: str, port: int, message: bytes) -> bytes:
    """Send an HL7 message over MLLP and return the raw ACK."""
    frame = START_BLOCK + message + END_BLOCK + CARRIAGE_RETURN
    with socket.create_connection((host, port)) as sock:
        sock.sendall(frame)
        ack = sock.recv(1024)
    return ack