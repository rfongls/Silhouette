from typing import get_origin
import pytest
from fhir.resources.encounter import Encounter


@pytest.mark.skipif(not hasattr(Encounter, "model_validate"), reason="requires fhir.resources>=7")
def test_encounter_class_alias_parses_dynamic():
    base = {
        "resourceType": "Encounter",
        "status": "finished",
    }
    f = Encounter.model_fields.get("class_fhir")
    ann = getattr(f, "annotation", None)
    wants_list = get_origin(ann) in (list, tuple)
    cls_val = {
        "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
        "code": "IMP",
    }
    res = dict(base, **({"class": [cls_val]} if wants_list else {"class": cls_val}))
    Encounter.model_validate(res)
