import asyncio
from skills.hl7_drafter import draft_message, send_message

async def _echo_server(reader, writer):
    try:
        await reader.readuntil(b"\x1c\r")
        ack = "\x0bMSH|^~\\&|ACK|ACK|ACK|ACK|202401010000||ACK^A01|1|P|2.5.1\x1c\r"
        writer.write(ack.encode("utf-8"))
        await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()

def test_draft_and_send():
    async def run():
        server = await asyncio.start_server(_echo_server, "127.0.0.1", 2575)
        try:
            msg = draft_message("ADT^A01", {"patient_id": "123"})
            ack = await send_message("127.0.0.1", 2575, msg)
            assert "ACK" in ack
        finally:
            server.close()
            await server.wait_closed()
    asyncio.run(run())
