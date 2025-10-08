"""Stub HL7 validation operator for Phase 1 scaffolding."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ..contracts import Issue, Message, Operator, Result
from ..registry import register_operator


@dataclass
class ValidateHL7Operator(Operator):
    """Placeholder operator that will wrap the production HL7 validator."""

    name: str
    profile: str | None = None
    strict: bool = False

    async def process(self, msg: Message) -> Result:
        note = self.profile or "default"
        issues = [
            Issue(
                severity="passed",
                code="validate.stub",
                message=f"Validated against {note} profile",
            )
        ]
        return Result(message=msg, issues=issues)


@register_operator("validate-hl7")
def _validate_operator(config: Mapping[str, object]) -> Operator:
    profile = config.get("profile")
    strict = bool(config.get("strict"))
    return ValidateHL7Operator(name="validate-hl7", profile=profile, strict=strict)
