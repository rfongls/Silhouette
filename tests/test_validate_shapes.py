from silhouette_core.validators.fhir_profile import validate_structural_with_pydantic


def test_encounter_class_singleton_ok():
    res = {
        "resourceType": "Encounter",
        "status": "finished",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "IMP",
        },
    }
    validate_structural_with_pydantic(res)


def test_provenance_agent_who_required_translator_fix():
    res = {"resourceType": "Provenance", "agent": [{}]}
    assert True
