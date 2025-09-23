from __future__ import annotations

from collections import defaultdict
import re

FIELD_SEP = "|"


def _get_field(parts: list[str], field_idx: int) -> str:
    pos = field_idx - 1
    if pos < 0 or pos >= len(parts):
        return ""
    return parts[pos]


def validate_message(text: str, profile: str | None = None) -> dict:
    """Placeholder validation that checks for key segments."""
    errors = defaultdict(int)
    warnings: list[str] = []
    lines = text.splitlines()
    if not any(l.startswith("MSH|") for l in lines):
        errors["Missing MSH"] += 1
    if not any(l.startswith("PID|") for l in lines):
        warnings.append("No PID segment found")
    return {"ok": len(errors) == 0, "errors": [f"{k} x{v}" for k, v in errors.items()], "warnings": warnings}


def validate_with_template(message_text: str, tpl: dict | None) -> dict[str, object]:
    """Validate HL7 content using a structured template."""

    checks = (tpl or {}).get("checks") or []
    issues: list[dict[str, object]] = []
    if not message_text:
        return {"ok": not checks, "issues": issues}

    segments: dict[str, list[list[str]]] = {}
    for line in message_text.splitlines():
        if not line.strip():
            continue
        parts = line.split(FIELD_SEP)
        seg = parts[0].strip().upper() if parts else ""
        if not seg:
            continue
        segments.setdefault(seg, []).append(parts)

    for raw in checks:
        if not isinstance(raw, dict):
            continue
        segment = (raw.get("segment") or "").strip().upper()
        field_val = raw.get("field")
        try:
            field_idx = int(field_val)
        except Exception:
            continue
        required = bool(raw.get("required", True))
        pattern = raw.get("pattern") or None
        allowed_values = raw.get("allowed_values") or None
        allowed_list = None
        if allowed_values:
            if isinstance(allowed_values, (list, tuple)):
                allowed_list = [str(v) for v in allowed_values if str(v).strip()]
            else:
                allowed_list = [s.strip() for s in re.split(r"[;,]", str(allowed_values)) if s.strip()]
        seg_rows = segments.get(segment, [])
        if not seg_rows:
            if required:
                issues.append(
                    {
                        "severity": "error",
                        "segment": segment,
                        "field": field_idx,
                        "code": "SEGMENT_MISSING",
                        "message": f"Segment {segment} missing",
                    }
                )
            continue
        for occ_idx, parts in enumerate(seg_rows):
            value = _get_field(parts, field_idx)
            if required and not value:
                issues.append(
                    {
                        "severity": "error",
                        "segment": segment,
                        "field": field_idx,
                        "occurrence": occ_idx,
                        "code": "REQUIRED_EMPTY",
                        "message": "Required field is empty",
                    }
                )
                continue
            if pattern:
                try:
                    if not re.search(str(pattern), value or ""):
                        issues.append(
                            {
                                "severity": "error",
                                "segment": segment,
                                "field": field_idx,
                                "occurrence": occ_idx,
                                "code": "PATTERN_MISMATCH",
                                "message": f"Value '{value}' does not match pattern {pattern}",
                            }
                        )
                except re.error as exc:
                    issues.append(
                        {
                            "severity": "error",
                            "segment": segment,
                            "field": field_idx,
                            "occurrence": occ_idx,
                            "code": "BAD_PATTERN",
                            "message": f"Invalid regex: {exc}",
                        }
                    )
            if allowed_list is not None and value not in allowed_list:
                issues.append(
                    {
                        "severity": "error",
                        "segment": segment,
                        "field": field_idx,
                        "occurrence": occ_idx,
                        "code": "VALUE_NOT_ALLOWED",
                        "message": f"Value '{value}' not allowed",
                    }
                )

    return {"ok": len(issues) == 0, "issues": issues}
