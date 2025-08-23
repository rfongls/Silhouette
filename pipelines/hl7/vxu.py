from __future__ import annotations

async def handle(message: str) -> None:
    if "PID|" not in message:
        raise ValueError("Missing PID segment")
    for line in message.split("\r"):
        if line.startswith("RXA|"):
            parts = line.split("|")
            if len(parts) > 5:
                code = parts[5].split("^")[0]
                if code in {"", "999999"}:
                    raise ValueError("Invalid CVX code")
    # success returns None
