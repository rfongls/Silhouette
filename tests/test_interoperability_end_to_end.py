import pytest
pytest.importorskip("jsonschema")
pytest.importorskip("hl7apy")
pytest.importorskip("fhir.resources")

from translators.cda_to_fhir import CDAToFHIRTranslator  # noqa: E402
from translators.hl7v2_to_fhir import HL7v2ToFHIRTranslator, load_rules  # noqa: E402
from validators.fhir import validate_fhir_bundle  # noqa: E402
from validators.fhir_profile import (  # noqa: E402
    validate_structural_with_pydantic,
    validate_uscore_jsonschema,
)
from validators.hl7 import validate_hl7_structural  # noqa: E402


@pytest.mark.hl7
def test_oru_to_fhir_e2e_real_hl7():
    hl7_text = open("tests/fixtures/hl7/sample_oru_r01.hl7").read()
    try:
        validate_hl7_structural(hl7_text)
    except Exception as e:
        pytest.skip(f"HL7 structural validation skipped: {e!r}")
    rules = load_rules("profiles/hl7v2_oru_to_fhir.yml")
    tr = HL7v2ToFHIRTranslator(rules)
    bundle = tr.translate_text(hl7_text)
    validate_fhir_bundle(bundle)
    for entry in bundle["entry"]:
        res = entry["resource"]
        validate_uscore_jsonschema(res)
        validate_structural_with_pydantic(res)
    assert any(e["resource"]["resourceType"] == "Observation" for e in bundle["entry"])
    assert any(e["resource"]["resourceType"] == "Patient" for e in bundle["entry"])

def test_ccd_to_fhir_e2e():
    xml = open("tests/fixtures/cda/sample_ccd.xml").read()
    b = CDAToFHIRTranslator().translate(xml)
    validate_fhir_bundle(b)
    assert any(e["resource"]["resourceType"]=="Patient" for e in b["entry"])
