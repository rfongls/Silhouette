import asyncio, yaml, pytest
from agents.hl7_agent import HL7Agent
from interfaces.hl7.mllp_server import MLLPServer
from interfaces.hl7.router import HL7Router

VXU_DATA = {"patient_id": "123456", "cvx_code": "208", "given": "JOHN", "family": "DOE", "dob": "19800101"}


async def _server(port=9027):
    routes = yaml.safe_load(open("config/routes.yaml"))
    router = HL7Router(routes)
    server = MLLPServer(router, "127.0.0.1", port)
    await server.run()


@pytest.mark.hl7
def test_agent_draft_send_vxu_ack():
    port = 9027
    async def run():
        task = asyncio.create_task(_server(port))
        await asyncio.sleep(0.25)
        res = await HL7Agent().draft_send("VXU^V04", VXU_DATA, "127.0.0.1", port)
        task.cancel()
        return res["ack"]
    ack = asyncio.run(run())
    assert "MSA|AA" in ack
