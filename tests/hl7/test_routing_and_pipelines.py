import yaml, asyncio, pytest
from interfaces.hl7.router import HL7Router

VXU_OK = ("MSH|^~\\&|IMM|SENDER|IIS|STATE|202402091030||VXU^V04|MSG2|P|2.5.1\r"
          "PID|1||123456^^^SENDER^MR||DOE^JOHN||19800101|M\r"
          "RXA|0|1|20240101||208^X^CVX|0.5|mL\r")
VXU_BAD = ("MSH|^~\\&|IMM|SENDER|IIS|STATE|202402091030||VXU^V04|MSG3|P|2.5.1\r"
           "RXA|0|1|20240101||208^X^CVX|0.5|mL\r")
VXU_BAD_CVX = ("MSH|^~\\&|IMM|SENDER|IIS|STATE|202402091030||VXU^V04|MSG4|P|2.5.1\r"
               "PID|1||123456^^^SENDER^MR\r"
               "RXA|0|1|20240101||999999^INVALID^CVX|0.5|mL\r")


def _run(router, msg):
    return asyncio.run(router.process(msg))


@pytest.mark.hl7
def test_route_vxu_ok():
    router = HL7Router(yaml.safe_load(open("config/routes.yaml")))
    ack = _run(router, VXU_OK)
    assert "MSA|AA|MSG2" in ack


@pytest.mark.hl7
def test_route_vxu_missing_pid():
    router = HL7Router(yaml.safe_load(open("config/routes.yaml")))
    ack = _run(router, VXU_BAD)
    assert "|AE|MSG3" in ack or "|AR|MSG3" in ack


@pytest.mark.hl7
def test_route_vxu_invalid_cvx():
    router = HL7Router(yaml.safe_load(open("config/routes.yaml")))
    ack = _run(router, VXU_BAD_CVX)
    assert "|AE|MSG4" in ack or "|AR|MSG4" in ack
