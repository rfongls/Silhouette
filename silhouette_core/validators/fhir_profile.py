from typing import Any, Dict, Type
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
    if hasattr(model, "model_validate"):
        model.model_validate(resource)
    else:
        model(**resource)


def validate_terminology(resource: Dict[str, Any], cache_dir: str | None) -> None:
    """Run lightweight terminology validation using the local cache."""
    if not terminology_service.validate_resource(resource, cache_dir=cache_dir):
        raise ValueError("Terminology check failed")
