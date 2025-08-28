import pytest
from skills.interoperability import InteropSkill

SAMPLE_HL7 = (
    "MSH|^~\\&|SIL|FAC|HIS|FAC|202501010101||ADT^A01|1|P|2.5\r"
    "PID|1||12345^^^MRN||Doe^John\r"
)


@pytest.mark.parametrize("kind,payload", [("hl7", SAMPLE_HL7)])
def test_validate_smoke(kind, payload):
    skill = InteropSkill()
    result = skill.validate(payload, kind)
    assert isinstance(result, dict)
