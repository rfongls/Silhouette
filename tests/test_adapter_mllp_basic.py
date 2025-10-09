import asyncio

from engine.adapters.mllp import MLLPAdapter


FRAME_ONE = (
    b"MSH|^~\\&|SENDER|FAC|REC|FAC|202501011200||ADT^A01|MSG0001|P|2.5\r"
    b"PID|1||12345^^^HOSP^MR||DOE^JOHN||19800101|M\r"
)

FRAME_TWO = (
    b"MSH|^~\\&|SENDER|FAC|REC|FAC|202501011300||ADT^A01|MSG0002|P|2.5\r"
    b"PID|1||67890^^^HOSP^MR||SMITH^JANE||19900101|F\r"
)


async def _send_frames(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    for frame in (FRAME_ONE, FRAME_TWO):
        writer.write(b"\x0b" + frame + b"\x1c\x0d")
        await writer.drain()
    writer.close()
    await writer.wait_closed()


def test_mllp_adapter_streams_framed_messages():
    async def _run() -> None:
        server = await asyncio.start_server(_send_frames, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        adapter = MLLPAdapter(name="mllp", host="127.0.0.1", port=port)
        messages = []
        async for message in adapter.stream():
            messages.append(message)
        assert len(messages) == 2
        assert messages[0].raw == FRAME_ONE
        assert messages[0].id == "mllp-1"
        assert messages[1].raw == FRAME_TWO
        assert messages[1].id == "mllp-2"
        server.close()
        await server.wait_closed()

    asyncio.run(_run())
