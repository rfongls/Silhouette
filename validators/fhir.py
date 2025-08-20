import json

def validate_fhir_bundle(bundle_json: str | dict) -> None:
    if isinstance(bundle_json, str):
        obj = json.loads(bundle_json)
    else:
        obj = bundle_json
    if obj.get("resourceType") != "Bundle":
        raise ValueError("Not a FHIR Bundle")
    if "entry" not in obj or not isinstance(obj["entry"], list):
        raise ValueError("Bundle.entry missing or invalid")
