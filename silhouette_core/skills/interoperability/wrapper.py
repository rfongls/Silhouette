from typing import Any

from validators.cda import CDAValidator
from validators.fhir import FHIRValidator
from validators.hl7 import HL7Validator


class InteropSkill:
    """Unified entry for HL7/FHIR/CDA validation.
    Thin facade to existing validators, matching docs' expected import path.
    """

    def __init__(self) -> None:
        self.hl7 = HL7Validator()
        self.fhir = FHIRValidator()
        self.cda = CDAValidator()

    def validate(self, payload: str, kind: str, **opts: dict[str, Any]) -> dict[str, Any]:
        kind = kind.lower()
        if kind == "hl7":
            return self.hl7.validate(payload, **opts)
        if kind == "fhir":
            return self.fhir.validate(payload, **opts)
        if kind == "cda":
            return self.cda.validate(payload, **opts)
        raise ValueError(f"Unsupported kind: {kind}")
