from silhouette_core.translators.x12_270_271 import parse_270, generate_271_response
from silhouette_core.translators.x12_278_275 import (
    translate_fhir_pas_to_278,
    attach_275,
)

def test_270_271_roundtrip():
    edi = open("tests/fixtures/x12/sample_270_eligibility.edi").read()
    req = parse_270(edi)
    resp = generate_271_response(req)
    assert "271" in resp

def test_278_pas_stub():
    pas = {"identifier":[{"value":"CTRL0007"}]}
    edi_278 = translate_fhir_pas_to_278(pas)
    assert "ST*278*CTRL0007" in edi_278
    hint = attach_275("<ClinicalAttachment/>")
    assert "275 attachment" in hint
