"""HL7 validation operator that wraps the V1 validation utilities."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from silhouette_core.validators.hl7 import (
    HL7Validator,
    validate_hl7_structural,
)

from ..contracts import Issue, Message, Operator, Result
from ..registry import register_operator

_DEFAULT_PROFILE = "default"


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _guess_segment(detail: str) -> str | None:
    upper = detail.upper()
    for seg in ("MSH", "PID", "PV1", "NK1"):
        if seg in upper:
            return seg
    return None


@dataclass
class ValidateHL7Operator(Operator):
    """Bridge the legacy HL7 validator into the Engine V2 runtime."""

    name: str
    profile: str | None = None
    strict: bool = False
    _validator: HL7Validator = field(default_factory=HL7Validator, init=False, repr=False)

    async def process(self, msg: Message) -> Result:
        text = msg.raw.decode("utf-8", errors="replace")
        issues: list[Issue] = []

        try:
            self._validator.validate(text, profile=self.profile or _DEFAULT_PROFILE)
        except Exception as exc:  # pragma: no cover - defensive mapping
            detail = str(exc) or "Validation failed"
            issues.append(
                Issue(
                    severity="error",
                    code="validate.error",
                    segment=_guess_segment(detail),
                    message=detail,
                )
            )
        else:
            note = self.profile or _DEFAULT_PROFILE
            issues.append(
                Issue(
                    severity="passed",
                    code="validate.ok",
                    message=f"HL7 validation passed for profile '{note}'",
                )
            )

        pv1_issue = self._check_required_segment(text, "PV1", strict=self.strict)
        if pv1_issue:
            issues.append(pv1_issue)

        structural_issue = self._run_structural_validation(text)
        if structural_issue:
            issues.append(structural_issue)

        return Result(message=msg, issues=issues)

    def _run_structural_validation(self, text: str) -> Issue | None:
        try:
            validate_hl7_structural(text)
        except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
            return Issue(
                severity="warning",
                code="validate.structural.unavailable",
                message=f"Structural validation unavailable: {exc}",
            )
        except ImportError as exc:  # pragma: no cover - optional dependency
            return Issue(
                severity="warning",
                code="validate.structural.unavailable",
                message=f"Structural validation unavailable: {exc}",
            )
        except Exception as exc:
            severity = "error" if self.strict else "warning"
            detail = str(exc) or "Structural validation failed"
            return Issue(
                severity=severity,
                code="validate.structural",
                message=detail,
            )
        return None

    @staticmethod
    def _check_required_segment(text: str, segment: str, *, strict: bool) -> Issue | None:
        if segment and f"{segment}|" not in text:
            return Issue(
                severity="error" if strict else "warning",
                code="validate.segment.missing",
                segment=segment,
                message=f"Required segment '{segment}' is missing",
            )
        return None


@register_operator("validate-hl7")
def _validate_operator(config: Mapping[str, object]) -> Operator:
    profile_raw = config.get("profile")
    profile = str(profile_raw).strip() if profile_raw else None
    strict = _to_bool(config.get("strict"))
    return ValidateHL7Operator(name="validate-hl7", profile=profile, strict=strict)
