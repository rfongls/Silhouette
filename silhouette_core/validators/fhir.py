import json


def validate_fhir_bundle(bundle_json: str | dict) -> None:
    obj = json.loads(bundle_json) if isinstance(bundle_json, str) else bundle_json
    if obj.get("resourceType") != "Bundle":
        raise ValueError("Not a FHIR Bundle")
    if "entry" not in obj or not isinstance(obj["entry"], list):
        raise ValueError("Bundle.entry missing or invalid")


class FHIRValidator:
    """Simple FHIR validator facade."""

    def validate(self, payload: str | dict, **opts: dict) -> dict:
        validate_fhir_bundle(payload)
        return {"valid": True}
