import asyncio, os, subprocess, tempfile, yaml, pytest
from pathlib import Path
from interfaces.hl7.mllp_server import MLLPServer
from interfaces.hl7.mllp_client import send
from interfaces.hl7.router import HL7Router

VXU = ("MSH|^~\\&|IMM|SENDER|IIS|STATE|202402091030||VXU^V04|MSGTLS|P|2.5.1\r"
       "PID|1||123456^^^SENDER^MR||DOE^JOHN||19800101|M\r"
       "RXA|0|1|20240101||208^Influenza, injectable, quadrivalent^CVX|0.5|mL\r")


@pytest.mark.hl7
@pytest.mark.tls
@pytest.mark.skipif(os.environ.get("RUN_TLS_TESTS") != "1", reason="RUN_TLS_TESTS!=1")
def test_mllp_tls_roundtrip():
    port = 9030
    async def run():
        with tempfile.TemporaryDirectory() as td:
            cert = Path(td) / "cert.pem"
            key = Path(td) / "key.pem"
            subprocess.run([
                "openssl", "req", "-x509", "-newkey", "rsa:2048", "-keyout", str(key),
                "-out", str(cert), "-days", "1", "-nodes", "-subj", "/CN=localhost"
            ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            routes = yaml.safe_load(open("config/routes.yaml"))
            router = HL7Router(routes)
            server = MLLPServer(router, "127.0.0.1", port, ssl_cert=str(cert), ssl_key=str(key))
            task = asyncio.create_task(server.run())
            await asyncio.sleep(0.25)
            ack = await send("127.0.0.1", port, VXU, tls=True, ca_cert=str(cert))
            task.cancel()
            return ack
    ack = asyncio.run(run())
    assert "MSA|AA|MSGTLS" in ack
