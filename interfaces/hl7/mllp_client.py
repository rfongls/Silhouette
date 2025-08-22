from __future__ import annotations
import asyncio, ssl
from typing import Optional


async def send(host: str, port: int, message: str, tls: bool = False, ca_cert: Optional[str] = None) -> str:
    ssl_ctx = None
    if tls:
        ssl_ctx = ssl.create_default_context(cafile=ca_cert) if ca_cert else ssl.create_default_context()
    reader, writer = await asyncio.open_connection(host, port, ssl=ssl_ctx)
    writer.write(b"\x0b" + message.encode("utf-8") + b"\x1c\x0d")
    await writer.drain()
    data = await reader.readuntil(b"\x1c\x0d")
    writer.close()
    try:
        await writer.wait_closed()
    except Exception:
        pass
    return data.decode("utf-8", errors="ignore").strip("\x0b\x1c\r")
