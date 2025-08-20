import json
import yaml
from translators.hl7v2_to_fhir import HL7v2ToFHIRTranslator, MappingRule
from translators.cda_to_fhir import CDAToFHIRTranslator
from validators.fhir import validate_fhir_bundle

def load_rules(path):
    raw = yaml.safe_load(open(path))
    rules = []
    for r in raw["resources"]:
        rules.append(MappingRule(**r))
    return rules

def test_oru_to_fhir_e2e():
    # Fake parsed HL7 dict to keep tests offline
    hl7 = {
        "PID": {"3": [{"1":"123456"}], "5": [{"1":"DOE","2":"JOHN"}], "7":"19800101"},
        "PV1": {"19":{"1":"12345"}},
        "OBR": {"4":{"1":"718-7"}},
        "OBX": [{"3":{"1":"718-7"}, "5":"13.6", "6":{"1":"g/dL"}},
                {"3":{"1":"4548-4"}, "5":"41.2", "6":{"1":"%"}}]
    }
    rules = load_rules("profiles/hl7v2_oru_to_fhir.yml")
    t = HL7v2ToFHIRTranslator(rules)
    bundle = t.translate(hl7)
    validate_fhir_bundle(bundle)
    exp = json.load(open("tests/fixtures/fhir/expected_oru_bundle.json"))
    assert exp["entry"][0]["resource"]["resourceType"] == "Patient"
    assert any(e["resource"]["resourceType"]=="Observation" for e in bundle["entry"])

def test_ccd_to_fhir_e2e():
    xml = open("tests/fixtures/cda/sample_ccd.xml").read()
    b = CDAToFHIRTranslator().translate(xml)
    validate_fhir_bundle(b)
    assert any(e["resource"]["resourceType"]=="Patient" for e in b["entry"])
