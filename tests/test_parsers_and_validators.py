from validators.hl7 import validate_hl7_minimal
from validators.fhir import validate_fhir_bundle
from validators.cda import validate_ccd_minimal

def test_hl7_validator():
    text = open("tests/fixtures/hl7/sample_oru_r01.hl7").read()
    validate_hl7_minimal(text)

def test_ccd_validator():
    text = open("tests/fixtures/cda/sample_ccd.xml").read()
    validate_ccd_minimal(text)

def test_fhir_validator():
    text = open("tests/fixtures/fhir/expected_oru_bundle.json").read()
    validate_fhir_bundle(text)
