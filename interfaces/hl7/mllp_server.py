from __future__ import annotations
import asyncio, ssl
from typing import Optional
from .router import HL7Router


class MLLPServer:
    def __init__(self, router: HL7Router, host: str, port: int, ssl_cert: Optional[str] = None, ssl_key: Optional[str] = None):
        self.router = router
        self.host = host
        self.port = port
        self.ssl_cert = ssl_cert
        self.ssl_key = ssl_key
        self.server: Optional[asyncio.AbstractServer] = None

    async def run(self) -> None:
        ssl_ctx = None
        if self.ssl_cert and self.ssl_key:
            ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_ctx.load_cert_chain(self.ssl_cert, self.ssl_key)
        self.server = await asyncio.start_server(self._handle, self.host, self.port, ssl=ssl_ctx)
        async with self.server:
            await self.server.serve_forever()

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        data = b""
        while True:
            chunk = await reader.read(1024)
            if not chunk:
                break
            data += chunk
            if b"\x1c\x0d" in data:
                break
        message = data.strip(b"\x0b").rstrip(b"\x1c\x0d").decode("utf-8", errors="ignore")
        ack = await self.router.process(message)
        writer.write(b"\x0b" + ack.encode("utf-8") + b"\x1c\x0d")
        await writer.drain()
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
