import asyncio, yaml, pytest
from interfaces.hl7.mllp_server import MLLPServer
from interfaces.hl7.mllp_client import send
from interfaces.hl7.router import HL7Router

VXU = ("MSH|^~\\&|IMM|SENDER|IIS|STATE|202402091030||VXU^V04|MSG1|P|2.5.1\r"
       "PID|1||123456^^^SENDER^MR||DOE^JOHN||19800101|M\r"
       "RXA|0|1|20240101||208^Influenza, injectable, quadrivalent^CVX|0.5|mL\r")


async def _server(port=9025):
    routes = yaml.safe_load(open("config/routes.yaml"))
    router = HL7Router(routes)
    srv = MLLPServer(router, "127.0.0.1", port)
    await srv.run()


@pytest.mark.hl7
def test_mllp_ack_roundtrip():
    port = 9025
    async def run():
        task = asyncio.create_task(_server(port))
        await asyncio.sleep(0.25)
        ack = await send("127.0.0.1", port, VXU)
        task.cancel()
        return ack
    ack = asyncio.run(run())
    assert "MSA|AA|MSG1" in ack
