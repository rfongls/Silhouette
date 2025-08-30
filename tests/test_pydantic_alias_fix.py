from fhir.resources.encounter import Encounter
import pytest


@pytest.mark.skipif(not hasattr(Encounter, "model_validate"), reason="requires fhir.resources>=7")
def test_encounter_class_alias_parses():
    res = {
        "resourceType": "Encounter",
        "status": "finished",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "IMP",
        },
    }
    Encounter.model_validate(res)
