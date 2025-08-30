from typing import Any, Dict, Type, get_origin
import json
import jsonschema
from jsonschema import validate as js_validate
from pydantic import BaseModel
from fhir.resources.bundle import Bundle
from fhir.resources.observation import Observation
from fhir.resources.patient import Patient
from fhir.resources.condition import Condition
from fhir.resources.medicationstatement import MedicationStatement
from fhir.resources.encounter import Encounter
from fhir.resources.diagnosticreport import DiagnosticReport
from fhir.resources.provenance import Provenance
from fhir.resources.specimen import Specimen
import pathlib
from silhouette_core import terminology_service

SCHEMA_DIR = pathlib.Path("schemas/fhir/uscore")

def _load(name: str) -> Dict[str, Any]:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))

SCHEMA_INDEX = {
    "Bundle": _load("Bundle.schema.json"),
    "Patient": _load("Patient.schema.json"),
    "Observation": _load("Observation.schema.json"),
    "Condition": _load("Condition.schema.json"),
    "MedicationStatement": _load("MedicationStatement.schema.json"),
    "Encounter": _load("Encounter.schema.json"),
    "DiagnosticReport": _load("DiagnosticReport.schema.json"),
}

MODEL_REGISTRY: Dict[str, Type[BaseModel]] = {
    "Bundle": Bundle,
    "Patient": Patient,
    "Observation": Observation,
    "Condition": Condition,
    "MedicationStatement": MedicationStatement,
    "Encounter": Encounter,
    "DiagnosticReport": DiagnosticReport,
    "Provenance": Provenance,
    "Specimen": Specimen,
}


def _normalize_singletons_to_lists(model: Type[BaseModel], data: dict) -> dict:
    """Coerce singleton values into one-item lists when model expects a list."""
    if not hasattr(model, "model_fields"):
        return data
    out = dict(data)
    for fname, finfo in model.model_fields.items():
        alias = getattr(finfo, "alias", None) or fname
        if alias not in out:
            continue
        ann = getattr(finfo, "annotation", None)
        origin = get_origin(ann)
        if origin in (list, tuple):
            val = out[alias]
            if val is None:
                continue
            if not isinstance(val, (list, tuple)):
                out[alias] = [val]
    return out


def _validate_model(model: Type[BaseModel], data: dict) -> None:
    """Pydantic validation respecting aliases and singleton→list coercion."""
    data = _normalize_singletons_to_lists(model, data)
    if hasattr(model, "model_validate"):
        model.model_validate(data)
    else:  # pragma: no cover
        model(**data)

def validate_uscore_jsonschema(resource: Dict[str, Any]) -> None:
    rtype = resource.get("resourceType")
    schema = SCHEMA_INDEX.get(rtype)
    if not schema:
        return
    js_validate(instance=resource, schema=schema)

def validate_structural_with_pydantic(resource: Dict[str, Any]) -> None:
    """Validate structure using pydantic FHIR models (alias aware)."""
    rtype = resource.get("resourceType")
    model = MODEL_REGISTRY.get(rtype)
    if not model:
        return
    _validate_model(model, resource)


def validate_terminology(resource: Dict[str, Any], cache_dir: str | None) -> None:
    """Run lightweight terminology validation using the local cache."""
    if not terminology_service.validate_resource(resource, cache_dir=cache_dir):
        raise ValueError("Terminology check failed")
