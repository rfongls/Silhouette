from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader
import datetime, asyncio

env = Environment(loader=FileSystemLoader(str(Path("templates/hl7"))), autoescape=False)

def draft_message(message_type: str, data: Dict[str, Any]) -> str:
    """Render an HL7 message from Jinja2 template."""
    name = message_type.replace("^", "_").replace(":", "_") + ".hl7.j2"
    template_path = Path("templates/hl7") / name
    if template_path.exists():
        tmpl = env.get_template(name)
    else:
        tmpl = env.get_template("generic.hl7.j2")
    ctx = {"message_type": message_type, "ts": datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S"), **data}
    return tmpl.render(**ctx).strip() + "\r"

async def send_message(host: str, port: int, message: str) -> str:
    """Send HL7 via MLLP and return the ACK."""
    reader, writer = await asyncio.open_connection(host, port)
    payload = "\x0b" + message + "\x1c\r"
    writer.write(payload.encode("utf-8"))
    await writer.drain()
    data = await reader.readuntil(b"\x1c\r")
    writer.close()
    await writer.wait_closed()
    return data.decode("utf-8").strip("\x0b\x1c\r")
