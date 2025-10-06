from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Any, Optional, Dict, List, Set, Tuple
import re
from collections import defaultdict
from urllib.parse import parse_qs
import json
import logging
import time
import uuid
import os
import sys
import inspect
from fastapi import APIRouter, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from starlette.datastructures import UploadFile
from silhouette_core.interop.hl7_mutate import (
    enrich_clinical_fields,
    ensure_unique_fields,
    load_template_text,
)
from silhouette_core.interop.deid import deidentify_message, apply_deid_with_template
from silhouette_core.interop.mllp import send_mllp_batch
from silhouette_core.interop.validate_workbook import validate_message, validate_with_template
from api.activity_log import log_activity
from api.debug_log import log_debug_message
from api.metrics import record_event

router = APIRouter()
logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="templates")
templates.env.filters["split"] = lambda s, sep=" ", maxsplit=-1: ("" if s is None else str(s)).split(sep, maxsplit)

DEID_DIR = Path("configs/interop/deid_templates")
VAL_DIR = Path("configs/interop/validate_templates")
for folder in (DEID_DIR, VAL_DIR):
    folder.mkdir(parents=True, exist_ok=True)


def _load_template(path: Path, name: str, kind: str) -> dict:
    target = path / f"{name}.json"
    if not target.exists():
        raise HTTPException(status_code=400, detail=f"{kind.title()} template '{name}' not found")
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - malformed template
        raise HTTPException(status_code=400, detail=f"Invalid {kind} template JSON: {exc}") from exc


def load_deid_template(name: str) -> dict:
    return _load_template(DEID_DIR, name, "de-identify")


def load_validation_template(name: str) -> dict:
    return _load_template(VAL_DIR, name, "validation")


def _preview(value: Any, limit: int = 160) -> str:
    """Return a short, printable preview for logging."""
    try:
        if isinstance(value, (bytes, bytearray)):
            text = value.decode("utf-8", errors="replace")
        else:
            text = str(value)
    except Exception:
        text = repr(value)
    text = text.replace("\r", "\\r").replace("\n", "\\n")
    if len(text) > limit:
        return f"{text[:limit]}…(+{len(text) - limit})"
    return text


def _debug_log(event: str, **fields: Any) -> None:
    parts = [event]
    for key, value in fields.items():
        parts.append(f"{key}={_preview(value)}")
    message = " | ".join(parts)
    if log_debug_message(message):
        logger.info(message)
        print(f"[interop_gen] {message}", file=sys.stderr, flush=True)
print("[interop_gen] robust router module imported", file=sys.stderr)
this_file = os.path.abspath(inspect.getfile(sys.modules[__name__]))
print(f"[interop_gen] using file: {this_file}", file=sys.stderr)


def _coerce_scalar(value: Any) -> Any:
    """Return a scalar when lists only contain a single value."""
    if isinstance(value, list) and len(value) == 1:
        return value[0]
    return value


def _maybe_load_deid_template(name: Any) -> dict | None:
    if not name:
        return None
    normalized = str(name).strip()
    if not normalized or normalized.lower() in {"builtin", "legacy", "none"}:
        return None
    return load_deid_template(normalized)
  

def _maybe_load_validation_template(name: Any) -> dict | None:
    if not name:
        return None
    normalized = str(name).strip()
    if not normalized or normalized.lower() in {"builtin", "legacy", "none"}:
        return None
    return load_validation_template(normalized)

_ISSUE_VALUE_PATTERNS = (
    re.compile(r"[Vv]alue ['\"]([^'\"]+)['\"]"),
    re.compile(r"got ['\"]([^'\"]+)['\"]"),
    re.compile(r"was ['\"]([^'\"]+)['\"]"),
)

def _parse_hl7_location(loc: Any):
    """Return (segment, field, component, subcomponent) parsed from an HL7 location string."""
    if loc in (None, "", "—"):
        return None, None, None, None
    text = str(loc).strip()
    if not text or text == "—":
        return None, None, None, None
    if "-" in text:
        segment, rest = text.split("-", 1)
    else:
        segment, rest = text, ""
    field = component = subcomponent = None
    if rest:
        rest = rest.replace("^", ".")
        pieces = [part for part in rest.split(".") if part]

        def _to_int(value: str):
            try:
                digits = "".join(ch for ch in value if ch.isdigit())
                return int(digits) if digits else None
            except Exception:
                return None

        if len(pieces) >= 1:
            field = _to_int(pieces[0])
        if len(pieces) >= 2:
            component = _to_int(pieces[1])
        if len(pieces) >= 3:
            subcomponent = _to_int(pieces[2])
    return (segment or None), field, component, subcomponent


def _extract_issue_value(message: Any) -> str | None:
    if not message:
        return None
    text = str(message)
    for pattern in _ISSUE_VALUE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        for group in match.groups():
            if group:
                return group
    return None

def _enrich_validate_issues(issues: Any) -> list[dict[str, Any]]:
    """Ensure validation issues expose code, segment, field, component, subcomponent."""
    enriched: list[dict[str, Any]] = []
    for issue in issues or []:
        if isinstance(issue, dict):
            item = dict(issue)
        else:
            item = {"message": str(issue)}
        seg = item.get("segment")
        field = item.get("field")
        component = item.get("component")
        subcomponent = item.get("subcomponent")
        location = item.get("location")
        parsed = _parse_hl7_location(location)
        seg = seg or parsed[0]
        if field in ("", None):
            field = parsed[1]
        if component in ("", None):
            component = parsed[2]
        if subcomponent in ("", None):
            subcomponent = parsed[3]
        severity = (item.get("severity") or "error").lower()
        if "warn" in severity:
            severity = "warning"
        elif "err" in severity or "fail" in severity:
            severity = "error"
        elif any(tag in severity for tag in ("info", "ok", "pass")):
            severity = "info"
        else:
            severity = severity or "error"
        message_text = item.get("message") or ""
        enriched.append(
            {
                "severity": severity,
                "code": item.get("code")
                or item.get("rule")
                or item.get("id")
                or item.get("type")
                or "",
                "segment": seg or "",
                "field": field,
                "component": component,
                "subcomponent": subcomponent,
                "location": location or "",
                "occurrence": item.get("occurrence"),
                "message": message_text,
                "value": item.get("value") or _extract_issue_value(message_text),
            }
        )
    return enriched


_ISSUE_VALUE_PATTERNS = (
    re.compile(r"[Vv]alue ['\"]([^'\"]+)['\"]"),
    re.compile(r"got ['\"]([^'\"]+)['\"]"),
    re.compile(r"was ['\"]([^'\"]+)['\"]"),
)


def _parse_hl7_location(loc: Any):
    """Return (segment, field, component, subcomponent) parsed from an HL7 location string."""
    if loc in (None, "", "—"):
        return None, None, None, None
    text = str(loc).strip()
    if not text or text == "—":
        return None, None, None, None
    if "-" in text:
        segment, rest = text.split("-", 1)
    else:
        segment, rest = text, ""
    field = component = subcomponent = None
    if rest:
        rest = rest.replace("^", ".")
        pieces = [part for part in rest.split(".") if part]

        def _to_int(value: str):
            try:
                digits = "".join(ch for ch in value if ch.isdigit())
                return int(digits) if digits else None
            except Exception:
                return None

        if len(pieces) >= 1:
            field = _to_int(pieces[0])
        if len(pieces) >= 2:
            component = _to_int(pieces[1])
        if len(pieces) >= 3:
            subcomponent = _to_int(pieces[2])
    return (segment or None), field, component, subcomponent


def _extract_issue_value(message: Any) -> str | None:
    if not message:
        return None
    text = str(message)
    for pattern in _ISSUE_VALUE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        for group in match.groups():
            if group:
                return group
    return None


def _enrich_validate_issues(issues: Any) -> list[dict[str, Any]]:
    """Ensure validation issues expose code, segment, field, component, subcomponent."""
    enriched: list[dict[str, Any]] = []
    for issue in issues or []:
        if isinstance(issue, dict):
            item = dict(issue)
        else:
            item = {"message": str(issue)}
        seg = item.get("segment")
        field = item.get("field")
        component = item.get("component")
        subcomponent = item.get("subcomponent")
        location = item.get("location")
        parsed = _parse_hl7_location(location)
        seg = seg or parsed[0]
        if field in ("", None):
            field = parsed[1]
        if component in ("", None):
            component = parsed[2]
        if subcomponent in ("", None):
            subcomponent = parsed[3]
        severity = (item.get("severity") or "error").lower()
        if "warn" in severity:
            severity = "warning"
        elif "err" in severity or "fail" in severity:
            severity = "error"
        elif any(tag in severity for tag in ("info", "ok", "pass")):
            severity = "info"
        else:
            severity = severity or "error"
        message_text = item.get("message") or ""
        enriched.append(
            {
                "severity": severity,
                "code": item.get("code")
                or item.get("rule")
                or item.get("id")
                or item.get("type")
                or "",
                "segment": seg or "",
                "field": field,
                "component": component,
                "subcomponent": subcomponent,
                "location": location or "",
                "occurrence": item.get("occurrence"),
                "message": message_text,
                "value": item.get("value") or _extract_issue_value(message_text),
            }
        )
    return enriched


def _hl7_value_for_position(
    message: str,
    segment: str | None,
    field: int | None,
    component: int | None = None,
    subcomponent: int | None = None,
) -> str | None:
    """Return the first value for the given HL7 segment/field position."""
    if not message or not segment or field is None:
        return None
    seg = segment.strip().upper()
    if not seg or field <= 0:
        return None
    for line in (message or "").splitlines():
        if not line.startswith(seg + "|"):
            continue
        parts = line.split("|")
        if len(parts) <= field:
            continue
        value = parts[field] or ""
        if component and component > 0:
            comp_parts = value.split("^")
            if len(comp_parts) >= component:
                value = comp_parts[component - 1] or ""
            else:
                value = ""
        if subcomponent and subcomponent > 0:
            sub_parts = value.split("&")
            if len(sub_parts) >= subcomponent:
                value = sub_parts[subcomponent - 1] or ""
            else:
                value = ""
        return value or None
    return None


def _build_success_rows(
    template: dict[str, Any] | None,
    issues: list[dict[str, Any]],
    message_text: str,
) -> list[dict[str, Any]]:
    """Create synthetic OK rows for checks that passed."""
    if not template:
        return []
    checks = (template or {}).get("checks") or []
    if not isinstance(checks, list):
        return []
    failed_fields: set[tuple[str | None, int | None]] = set()
    failed_components: set[tuple[str | None, int | None, int | None, int | None]] = set()
    for issue in issues:
        sev = (issue.get("severity") or "").lower()
        if sev in {"error", "warning"}:
            seg_key = (issue.get("segment") or "").strip().upper() or None
            failed_fields.add((seg_key, issue.get("field")))
            failed_components.add(
                (
                    seg_key,
                    issue.get("field"),
                    issue.get("component"),
                    issue.get("subcomponent"),
                )
            )

    success_rows: list[dict[str, Any]] = []
    for raw in checks:
        if not isinstance(raw, dict):
            continue
        segment = (raw.get("segment") or "").strip().upper()
        field_val = raw.get("field")
        try:
            field_int = int(field_val)
        except Exception:
            continue
        seg_key = (segment or "").strip().upper() or None
        comp_val = raw.get("component")
        sub_val = raw.get("subcomponent")
        try:
            comp_int = int(comp_val) if comp_val not in (None, "") else None
        except Exception:
            comp_int = None
        try:
            sub_int = int(sub_val) if sub_val not in (None, "") else None
        except Exception:
            sub_int = None
        if (seg_key, field_int) in failed_fields:
            continue
        if (seg_key, field_int, comp_int, sub_int) in failed_components:
            continue
        value = _hl7_value_for_position(message_text, segment or None, field_int, comp_int, sub_int)
        success_rows.append(
            {
                "severity": "ok",
                "code": "OK",
                "segment": segment or "",
                "field": field_int,
                "component": comp_int,
                "subcomponent": sub_int,
                "occurrence": None,
                "location": f"{segment}-{field_int}" if segment else "",
                "message": "",
                "value": value,
            }
        )
    return success_rows


def _count_issue_severities(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"ok": 0, "warnings": 0, "errors": 0}
    for row in rows:
        sev = (row.get("severity") or "").lower()
        if sev == "ok":
            counts["ok"] += 1
        elif sev == "warning":
            counts["warnings"] += 1
        elif sev == "error":
            counts["errors"] += 1
    return counts


_ISSUE_VALUE_PATTERNS = (
    re.compile(r"[Vv]alue ['\"]([^'\"]+)['\"]"),
    re.compile(r"got ['\"]([^'\"]+)['\"]"),
    re.compile(r"was ['\"]([^'\"]+)['\"]"),
)


def _parse_hl7_location(loc: Any):
    """Return (segment, field, component, subcomponent) parsed from an HL7 location string."""
    if loc in (None, "", "—"):
        return None, None, None, None
    text = str(loc).strip()
    if not text or text == "—":
        return None, None, None, None
    if "-" in text:
        segment, rest = text.split("-", 1)
    else:
        segment, rest = text, ""
    field = component = subcomponent = None
    if rest:
        rest = rest.replace("^", ".")
        pieces = [part for part in rest.split(".") if part]

        def _to_int(value: str):
            try:
                digits = "".join(ch for ch in value if ch.isdigit())
                return int(digits) if digits else None
            except Exception:
                return None

        if len(pieces) >= 1:
            field = _to_int(pieces[0])
        if len(pieces) >= 2:
            component = _to_int(pieces[1])
        if len(pieces) >= 3:
            subcomponent = _to_int(pieces[2])
    return (segment or None), field, component, subcomponent


def _extract_issue_value(message: Any) -> str | None:
    if not message:
        return None
    text = str(message)
    for pattern in _ISSUE_VALUE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        for group in match.groups():
            if group:
                return group
    return None


def _hl7_separators(message: str) -> tuple[str, str, str, str]:
    """Return (field, component, repetition, subcomponent) separators."""
    default = ("|", "^", "~", "&")
    if not message:
        return default
    first_line = ""
    for line in message.splitlines():
        if line.strip():
            first_line = line
            break
    if not first_line.startswith("MSH") or len(first_line) < 8:
        return default
    field_sep = first_line[3]
    enc = first_line[4:8]
    comp = enc[0] if len(enc) >= 1 else "^"
    rep = enc[1] if len(enc) >= 2 else "~"
    sub = enc[3] if len(enc) >= 4 else "&"
    return field_sep or "|", comp or "^", rep or "~", sub or "&"


def _enrich_validate_issues(issues: Any, message_text: str) -> list[dict[str, Any]]:
    """Ensure validation issues expose code, segment, field, component, subcomponent."""
    enriched: list[dict[str, Any]] = []
    message_text = message_text or ""
    for issue in issues or []:
        if isinstance(issue, dict):
            item = dict(issue)
        else:
            item = {"message": str(issue)}
        seg = item.get("segment")
        field = item.get("field")
        component = item.get("component")
        subcomponent = item.get("subcomponent")
        location = item.get("location")
        parsed = _parse_hl7_location(location)
        seg = (seg or parsed[0] or "").strip().upper()

        def _coerce_int(value: Any) -> int | None:
            if value in ("", None, "—"):
                return None
            if isinstance(value, int):
                return value
            try:
                text = str(value).strip()
            except Exception:
                return None
            digits = "".join(ch for ch in text if ch.isdigit())
            return int(digits) if digits else None

        field = _coerce_int(field) if field is not None else parsed[1]
        if field is None:
            field = parsed[1]
        component = _coerce_int(component) if component is not None else parsed[2]
        if component is None:
            component = parsed[2]
        subcomponent = _coerce_int(subcomponent) if subcomponent is not None else parsed[3]
        if subcomponent is None:
            subcomponent = parsed[3]

        severity_raw = (item.get("severity") or "error").lower()
        if "warn" in severity_raw:
            severity = "warning"
        elif any(tag in severity_raw for tag in ("err", "fail")):
            severity = "error"
        elif any(tag in severity_raw for tag in ("ok", "pass", "success", "info")):
            severity = "ok"
        else:
            severity = severity_raw or "error"

        message_body = item.get("message") or ""
        value = item.get("value") or _extract_issue_value(message_body)
        if value in (None, ""):
            value = _hl7_value_for_position(
                message_text,
                seg,
                field,
                component,
                subcomponent,
            )

        enriched.append(
            {
                "severity": severity,
                "code": item.get("code")
                or item.get("rule")
                or item.get("id")
                or item.get("type")
                or "",
                "segment": seg or "",
                "field": field,
                "component": component,
                "subcomponent": subcomponent,
                "location": location or "",
                "occurrence": item.get("occurrence"),
                "message": message_body,
                "value": value,
            }
        )
    return enriched


def _hl7_value_for_position(
    message: str,
    segment: str | None,
    field: int | None,
    component: int | None = None,
    subcomponent: int | None = None,
) -> str | None:
    """Return the first value for the given HL7 segment/field position."""
    if not message or not segment or field is None:
        return None
    seg = segment.strip().upper()
    if not seg or field <= 0:
        return None
    field_sep, comp_sep, _, sub_sep = _hl7_separators(message)
    for line in (message or "").splitlines():
        if not line.startswith(seg + field_sep):
            continue
        parts = line.split(field_sep)
        if seg == "MSH":
            if field == 1:
                return field_sep
            idx = field - 1
        else:
            idx = field
        if idx >= len(parts):
            continue
        value = parts[idx] or ""
        if component and component > 0:
            comp_parts = value.split(comp_sep)
            if len(comp_parts) >= component:
                value = comp_parts[component - 1] or ""
            else:
                value = ""
        if subcomponent and subcomponent > 0:
            sub_parts = value.split(sub_sep)
            if len(sub_parts) >= subcomponent:
                value = sub_parts[subcomponent - 1] or ""
            else:
                value = ""
        return value or None
    return None


def _build_success_rows(
    template: dict[str, Any] | None,
    issues: list[dict[str, Any]],
    message_text: str,
) -> list[dict[str, Any]]:
    """Create synthetic OK rows for checks that passed."""
    if not template:
        return []
    checks = (template or {}).get("checks") or []
    if not isinstance(checks, list):
        return []
    failed_fields: set[tuple[str | None, int | None]] = set()
    failed_components: set[tuple[str | None, int | None, int | None, int | None]] = set()
    for issue in issues:
        sev = (issue.get("severity") or "").lower()
        if sev in {"error", "warning"}:
            seg_key = (issue.get("segment") or "").strip().upper() or None
            failed_fields.add((seg_key, issue.get("field")))
            failed_components.add(
                (
                    seg_key,
                    issue.get("field"),
                    issue.get("component"),
                    issue.get("subcomponent"),
                )
            )

    success_rows: list[dict[str, Any]] = []
    for raw in checks:
        if not isinstance(raw, dict):
            continue
        segment = (raw.get("segment") or "").strip().upper()
        field_val = raw.get("field")
        try:
            field_int = int(field_val)
        except Exception:
            continue
        seg_key = (segment or "").strip().upper() or None
        comp_val = raw.get("component")
        sub_val = raw.get("subcomponent")
        try:
            comp_int = int(comp_val) if comp_val not in (None, "") else None
        except Exception:
            comp_int = None
        try:
            sub_int = int(sub_val) if sub_val not in (None, "") else None
        except Exception:
            sub_int = None
        if (seg_key, field_int) in failed_fields:
            continue
        if (seg_key, field_int, comp_int, sub_int) in failed_components:
            continue
        value = _hl7_value_for_position(message_text, segment or None, field_int, comp_int, sub_int)
        success_rows.append(
            {
                "severity": "ok",
                "code": "OK",
                "segment": segment or "",
                "field": field_int,
                "component": comp_int,
                "subcomponent": sub_int,
                "occurrence": None,
                "location": f"{segment}-{field_int}" if segment else "",
                "message": "",
                "value": value,
            }
        )
    return success_rows


def _count_issue_severities(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"ok": 0, "warnings": 0, "errors": 0}
    for row in rows:
        sev = (row.get("severity") or "").lower()
        if sev == "ok":
            counts["ok"] += 1
        elif sev == "warning":
            counts["warnings"] += 1
        elif sev == "error":
            counts["errors"] += 1
    return counts


_ISSUE_VALUE_PATTERNS = (
    re.compile(r"[Vv]alue ['\"]([^'\"]+)['\"]"),
    re.compile(r"got ['\"]([^'\"]+)['\"]"),
    re.compile(r"was ['\"]([^'\"]+)['\"]"),
)


def _parse_hl7_location(loc: Any):
    """Return (segment, field, component, subcomponent) parsed from an HL7 location string."""
    if loc in (None, "", "—"):
        return None, None, None, None
    text = str(loc).strip()
    if not text or text == "—":
        return None, None, None, None
    if "-" in text:
        segment, rest = text.split("-", 1)
    else:
        segment, rest = text, ""
    field = component = subcomponent = None
    if rest:
        rest = rest.replace("^", ".")
        pieces = [part for part in rest.split(".") if part]

        def _to_int(value: str):
            try:
                digits = "".join(ch for ch in value if ch.isdigit())
                return int(digits) if digits else None
            except Exception:
                return None

        if len(pieces) >= 1:
            field = _to_int(pieces[0])
        if len(pieces) >= 2:
            component = _to_int(pieces[1])
        if len(pieces) >= 3:
            subcomponent = _to_int(pieces[2])
    return (segment or None), field, component, subcomponent


def _extract_issue_value(message: Any) -> str | None:
    if not message:
        return None
    text = str(message)
    for pattern in _ISSUE_VALUE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        for group in match.groups():
            if group:
                return group
    return None


def _hl7_separators(message: str) -> tuple[str, str, str, str]:
    """Return (field, component, repetition, subcomponent) separators."""
    default = ("|", "^", "~", "&")
    if not message:
        return default
    first_line = ""
    for line in message.splitlines():
        if line.strip():
            first_line = line
            break
    if not first_line.startswith("MSH") or len(first_line) < 8:
        return default
    field_sep = first_line[3]
    enc = first_line[4:8]
    comp = enc[0] if len(enc) >= 1 else "^"
    rep = enc[1] if len(enc) >= 2 else "~"
    sub = enc[3] if len(enc) >= 4 else "&"
    return field_sep or "|", comp or "^", rep or "~", sub or "&"


def _enrich_validate_issues(issues: Any, message_text: str) -> list[dict[str, Any]]:
    """Ensure validation issues expose code, segment, field, component, subcomponent."""
    enriched: list[dict[str, Any]] = []
    message_text = message_text or ""
    for issue in issues or []:
        if isinstance(issue, dict):
            item = dict(issue)
        else:
            item = {"message": str(issue)}
        seg = item.get("segment")
        field = item.get("field")
        component = item.get("component")
        subcomponent = item.get("subcomponent")
        location = item.get("location")
        parsed = _parse_hl7_location(location)
        seg = (seg or parsed[0] or "").strip().upper()

        def _coerce_int(value: Any) -> int | None:
            if value in ("", None, "—"):
                return None
            if isinstance(value, int):
                return value
            try:
                text = str(value).strip()
            except Exception:
                return None
            digits = "".join(ch for ch in text if ch.isdigit())
            return int(digits) if digits else None

        field = _coerce_int(field) if field is not None else parsed[1]
        if field is None:
            field = parsed[1]
        component = _coerce_int(component) if component is not None else parsed[2]
        if component is None:
            component = parsed[2]
        subcomponent = _coerce_int(subcomponent) if subcomponent is not None else parsed[3]
        if subcomponent is None:
            subcomponent = parsed[3]

        severity_raw = (item.get("severity") or "error").lower()
        if "warn" in severity_raw:
            severity = "warning"
        elif any(tag in severity_raw for tag in ("err", "fail")):
            severity = "error"
        elif any(tag in severity_raw for tag in ("ok", "pass", "success", "info")):
            severity = "ok"
        else:
            severity = severity_raw or "error"

        message_body = item.get("message") or ""
        value = item.get("value") or _extract_issue_value(message_body)
        if value in (None, ""):
            value = _hl7_value_for_position(
                message_text,
                seg,
                field,
                component,
                subcomponent,
            )

        enriched.append(
            {
                "severity": severity,
                "code": item.get("code")
                or item.get("rule")
                or item.get("id")
                or item.get("type")
                or "",
                "segment": seg or "",
                "field": field,
                "component": component,
                "subcomponent": subcomponent,
                "location": location or "",
                "occurrence": item.get("occurrence"),
                "message": message_body,
                "value": value,
            }
        )
    return enriched


def _hl7_value_for_position(
    message: str,
    segment: str | None,
    field: int | None,
    component: int | None = None,
    subcomponent: int | None = None,
) -> str | None:
    """Return the first value for the given HL7 segment/field position."""
    if not message or not segment or field is None:
        return None
    seg = segment.strip().upper()
    if not seg or field <= 0:
        return None
    field_sep, comp_sep, _, sub_sep = _hl7_separators(message)
    for line in (message or "").splitlines():
        if not line.startswith(seg + field_sep):
            continue
        parts = line.split(field_sep)
        if seg == "MSH":
            if field == 1:
                return field_sep
            idx = field - 1
        else:
            idx = field
        if idx >= len(parts):
            continue
        value = parts[idx] or ""
        if component and component > 0:
            comp_parts = value.split(comp_sep)
            if len(comp_parts) >= component:
                value = comp_parts[component - 1] or ""
            else:
                value = ""
        if subcomponent and subcomponent > 0:
            sub_parts = value.split(sub_sep)
            if len(sub_parts) >= subcomponent:
                value = sub_parts[subcomponent - 1] or ""
            else:
                value = ""
        return value or None
    return None


def _build_success_rows(
    template: dict[str, Any] | None,
    issues: list[dict[str, Any]],
    message_text: str,
) -> list[dict[str, Any]]:
    """Create synthetic OK rows for checks that passed."""
    if not template:
        return []
    checks = (template or {}).get("checks") or []
    if not isinstance(checks, list):
        return []
    failed_fields: set[tuple[str | None, int | None]] = set()
    failed_components: set[tuple[str | None, int | None, int | None, int | None]] = set()
    for issue in issues:
        sev = (issue.get("severity") or "").lower()
        if sev in {"error", "warning"}:
            seg_key = (issue.get("segment") or "").strip().upper() or None
            failed_fields.add((seg_key, issue.get("field")))
            failed_components.add(
                (
                    seg_key,
                    issue.get("field"),
                    issue.get("component"),
                    issue.get("subcomponent"),
                )
            )

    success_rows: list[dict[str, Any]] = []
    for raw in checks:
        if not isinstance(raw, dict):
            continue
        segment = (raw.get("segment") or "").strip().upper()
        field_val = raw.get("field")
        try:
            field_int = int(field_val)
        except Exception:
            continue
        seg_key = (segment or "").strip().upper() or None
        comp_val = raw.get("component")
        sub_val = raw.get("subcomponent")
        try:
            comp_int = int(comp_val) if comp_val not in (None, "") else None
        except Exception:
            comp_int = None
        try:
            sub_int = int(sub_val) if sub_val not in (None, "") else None
        except Exception:
            sub_int = None
        if (seg_key, field_int) in failed_fields:
            continue
        if (seg_key, field_int, comp_int, sub_int) in failed_components:
            continue
        value = _hl7_value_for_position(message_text, segment or None, field_int, comp_int, sub_int)
        success_rows.append(
            {
                "severity": "ok",
                "code": "OK",
                "segment": segment or "",
                "field": field_int,
                "component": comp_int,
                "subcomponent": sub_int,
                "occurrence": None,
                "location": f"{segment}-{field_int}" if segment else "",
                "message": "",
                "value": value,
            }
        )
    return success_rows


def _count_issue_severities(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"ok": 0, "warnings": 0, "errors": 0}
    for row in rows:
        sev = (row.get("severity") or "").lower()
        if sev == "ok":
            counts["ok"] += 1
        elif sev == "warning":
            counts["warnings"] += 1
        elif sev == "error":
            counts["errors"] += 1
    return counts


_ISSUE_VALUE_PATTERNS = (
    re.compile(r"[Vv]alue ['\"]([^'\"]+)['\"]"),
    re.compile(r"got ['\"]([^'\"]+)['\"]"),
    re.compile(r"was ['\"]([^'\"]+)['\"]"),
)


def _parse_hl7_location(loc: Any):
    """Return (segment, field, component, subcomponent) parsed from an HL7 location string."""
    if loc in (None, "", "—"):
        return None, None, None, None
    text = str(loc).strip()
    if not text or text == "—":
        return None, None, None, None
    if "-" in text:
        segment, rest = text.split("-", 1)
    else:
        segment, rest = text, ""
    field = component = subcomponent = None
    if rest:
        rest = rest.replace("^", ".")
        pieces = [part for part in rest.split(".") if part]

        def _to_int(value: str):
            try:
                digits = "".join(ch for ch in value if ch.isdigit())
                return int(digits) if digits else None
            except Exception:
                return None

        if len(pieces) >= 1:
            field = _to_int(pieces[0])
        if len(pieces) >= 2:
            component = _to_int(pieces[1])
        if len(pieces) >= 3:
            subcomponent = _to_int(pieces[2])
    return (segment or None), field, component, subcomponent


def _extract_issue_value(message: Any) -> str | None:
    if not message:
        return None
    text = str(message)
    for pattern in _ISSUE_VALUE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        for group in match.groups():
            if group:
                return group
    return None


def _hl7_separators(message: str) -> tuple[str, str, str, str]:
    """Return (field, component, repetition, subcomponent) separators."""
    default = ("|", "^", "~", "&")
    if not message:
        return default
    first_line = ""
    for line in message.splitlines():
        if line.strip():
            first_line = line
            break
    if not first_line.startswith("MSH") or len(first_line) < 8:
        return default
    field_sep = first_line[3]
    enc = first_line[4:8]
    comp = enc[0] if len(enc) >= 1 else "^"
    rep = enc[1] if len(enc) >= 2 else "~"
    sub = enc[3] if len(enc) >= 4 else "&"
    return field_sep or "|", comp or "^", rep or "~", sub or "&"


def _enrich_validate_issues(issues: Any, message_text: str) -> list[dict[str, Any]]:
    """Ensure validation issues expose code, segment, field, component, subcomponent."""
    enriched: list[dict[str, Any]] = []
    message_text = message_text or ""
    for issue in issues or []:
        if isinstance(issue, dict):
            item = dict(issue)
        else:
            item = {"message": str(issue)}
        seg = item.get("segment")
        field = item.get("field")
        component = item.get("component")
        subcomponent = item.get("subcomponent")
        location = item.get("location")
        parsed = _parse_hl7_location(location)
        seg = (seg or parsed[0] or "").strip().upper()

        def _coerce_int(value: Any) -> int | None:
            if value in ("", None, "—"):
                return None
            if isinstance(value, int):
                return value
            try:
                text = str(value).strip()
            except Exception:
                return None
            digits = "".join(ch for ch in text if ch.isdigit())
            return int(digits) if digits else None

        field = _coerce_int(field) if field is not None else parsed[1]
        if field is None:
            field = parsed[1]
        component = _coerce_int(component) if component is not None else parsed[2]
        if component is None:
            component = parsed[2]
        subcomponent = _coerce_int(subcomponent) if subcomponent is not None else parsed[3]
        if subcomponent is None:
            subcomponent = parsed[3]

        severity_raw = (item.get("severity") or "error").lower()
        if "warn" in severity_raw:
            severity = "warning"
        elif any(tag in severity_raw for tag in ("err", "fail")):
            severity = "error"
        elif any(tag in severity_raw for tag in ("ok", "pass", "success", "info")):
            severity = "ok"
        else:
            severity = severity_raw or "error"

        message_body = item.get("message") or ""
        value = item.get("value") or _extract_issue_value(message_body)
        if value in (None, ""):
            value = _hl7_value_for_position(
                message_text,
                seg,
                field,
                component,
                subcomponent,
            )

        enriched.append(
            {
                "severity": severity,
                "code": item.get("code")
                or item.get("rule")
                or item.get("id")
                or item.get("type")
                or "",
                "segment": seg or "",
                "field": field,
                "component": component,
                "subcomponent": subcomponent,
                "location": location or "",
                "occurrence": item.get("occurrence"),
                "message": message_body,
                "value": value,
            }
        )
    return enriched


def _hl7_value_for_position(
    message: str,
    segment: str | None,
    field: int | None,
    component: int | None = None,
    subcomponent: int | None = None,
) -> str | None:
    """Return the first value for the given HL7 segment/field position."""
    if not message or not segment or field is None:
        return None
    seg = segment.strip().upper()
    if not seg or field <= 0:
        return None
    field_sep, comp_sep, _, sub_sep = _hl7_separators(message)
    for line in (message or "").splitlines():
        if not line.startswith(seg + field_sep):
            continue
        parts = line.split(field_sep)
        if seg == "MSH":
            if field == 1:
                return field_sep
            idx = field - 1
        else:
            idx = field
        if idx >= len(parts):
            continue
        value = parts[idx] or ""
        if component and component > 0:
            comp_parts = value.split(comp_sep)
            if len(comp_parts) >= component:
                value = comp_parts[component - 1] or ""
            else:
                value = ""
        if subcomponent and subcomponent > 0:
            sub_parts = value.split(sub_sep)
            if len(sub_parts) >= subcomponent:
                value = sub_parts[subcomponent - 1] or ""
            else:
                value = ""
        return value or None
    return None


def _build_success_rows(
    template: dict[str, Any] | None,
    issues: list[dict[str, Any]],
    message_text: str,
) -> list[dict[str, Any]]:
    """Create synthetic OK rows for checks that passed."""
    if not template:
        return []
    checks = (template or {}).get("checks") or []
    if not isinstance(checks, list):
        return []
    failed_fields: set[tuple[str | None, int | None]] = set()
    failed_components: set[tuple[str | None, int | None, int | None, int | None]] = set()
    for issue in issues:
        sev = (issue.get("severity") or "").lower()
        if sev in {"error", "warning"}:
            seg_key = (issue.get("segment") or "").strip().upper() or None
            failed_fields.add((seg_key, issue.get("field")))
            failed_components.add(
                (
                    seg_key,
                    issue.get("field"),
                    issue.get("component"),
                    issue.get("subcomponent"),
                )
            )

    success_rows: list[dict[str, Any]] = []
    for raw in checks:
        if not isinstance(raw, dict):
            continue
        segment = (raw.get("segment") or "").strip().upper()
        field_val = raw.get("field")
        try:
            field_int = int(field_val)
        except Exception:
            continue
        seg_key = (segment or "").strip().upper() or None
        comp_val = raw.get("component")
        sub_val = raw.get("subcomponent")
        try:
            comp_int = int(comp_val) if comp_val not in (None, "") else None
        except Exception:
            comp_int = None
        try:
            sub_int = int(sub_val) if sub_val not in (None, "") else None
        except Exception:
            sub_int = None
        if (seg_key, field_int) in failed_fields:
            continue
        if (seg_key, field_int, comp_int, sub_int) in failed_components:
            continue
        value = _hl7_value_for_position(message_text, segment or None, field_int, comp_int, sub_int)
        success_rows.append(
            {
                "severity": "ok",
                "code": "OK",
                "segment": segment or "",
                "field": field_int,
                "component": comp_int,
                "subcomponent": sub_int,
                "occurrence": None,
                "location": f"{segment}-{field_int}" if segment else "",
                "message": "",
                "value": value,
            }
        )
    return success_rows


def _count_issue_severities(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"ok": 0, "warnings": 0, "errors": 0}
    for row in rows:
        sev = (row.get("severity") or "").lower()
        if sev == "ok":
            counts["ok"] += 1
        elif sev == "warning":
            counts["warnings"] += 1
        elif sev == "error":
            counts["errors"] += 1
    return counts


async def parse_any_request(request: Request) -> dict:
    """Parse JSON, multipart, urlencoded, or query data into a dict."""
    ctype = (request.headers.get("content-type") or "").lower()
    try:
        query = dict(request.query_params)
    except KeyError:
        query = {}
    raw = await request.body()
    query_string = request.scope.get("query_string", b"")
    if isinstance(query_string, bytes):
        query_text = query_string.decode("latin-1", errors="ignore")
    else:
        query_text = str(query_string)
    _debug_log(
        "parse_any_request.start",
        method=request.method,
        path=request.url.path,
        query=query_text,
        ctype=ctype,
        content_length=request.headers.get("content-length"),
        hx=request.headers.get("hx-request"),
        raw_preview=_preview(raw),
    )

    body: dict[str, Any] = {}

    if raw and ("application/json" in ctype or "text/json" in ctype):
        try:
            parsed = json.loads(raw.decode("utf-8"))
            if isinstance(parsed, dict):
                body = dict(parsed)
        except Exception:
            body = {}

    if not body and "multipart/form-data" in ctype:
        try:
            form = await request.form()
            data: dict[str, Any] = {}
            for key, value in form.multi_items():
                if isinstance(value, UploadFile):
                    data.setdefault(key, value.filename)
                else:
                    data.setdefault(key, value)
            for key, value in query.items():
                data.setdefault(key, value)
            body = {k: _coerce_scalar(v) for k, v in data.items()}
        except Exception:
            body = {}

    if not body and "application/x-www-form-urlencoded" in ctype:
        try:
            form = await request.form()
            body = {key: form.get(key) for key in form.keys()} if form else {}
        except Exception:
            body = {}

    if not body and raw:
        try:
            parsed = parse_qs(raw.decode("utf-8", errors="replace"), keep_blank_values=True)
            body = {k: _coerce_scalar(v) for k, v in parsed.items()}
        except Exception:
            body = {}

    for key, value in query.items():
        body.setdefault(key, value)

    if "count" in body:
        try:
            body["count"] = int(body["count"])
        except Exception:
            pass

    if not body.get("trigger"):
        rel = str(body.get("template_relpath") or "").strip()
        if rel:
            stem = Path(rel).stem
            if stem:
                body["trigger"] = stem

    try:
        cnt_value = body.get("count", 1)
        if isinstance(cnt_value, str):
            cnt = int(cnt_value) if cnt_value.strip() else 1
        else:
            cnt = int(cnt_value)
    except Exception:
        cnt = 1
    deid_value = body.get("deidentify")
    missing_deidentify = "deidentify" not in body
    if not missing_deidentify:
        if deid_value is None:
            missing_deidentify = True
        elif isinstance(deid_value, str):
            missing_deidentify = deid_value.strip() == ""
    if cnt > 1 and missing_deidentify:
        body["deidentify"] = True

    _debug_log("parse_any_request.done", parsed_body=body)
    return body

TEMPLATES_HL7_DIR = (Path(__file__).resolve().parent.parent / "templates" / "hl7").resolve()
VALID_VERSIONS = {"hl7-v2-3", "hl7-v2-4", "hl7-v2-5"}
ALLOWED_EXTS = (".hl7", ".txt", ".hl7.j2")


def _assert_rel_under_templates(relpath: str) -> Path:
    p = (TEMPLATES_HL7_DIR / relpath).resolve()
    if not str(p).startswith(str(TEMPLATES_HL7_DIR)):
        raise HTTPException(status_code=400, detail="Invalid relpath")
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail=f"Template not found: {relpath}")
    return p


def _to_bool(v):
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    return s in ("1", "true", "on", "yes")


def _to_int(v, default=None):
    try:
        return int(v)
    except Exception:
        return default


def _stem_for_match(name: str) -> str:
    n = name
    if n.lower().endswith(".j2"):
        n = n[:-3]
    for ext in (".hl7", ".txt"):
        if n.lower().endswith(ext):
            n = n[: -len(ext)]
    return Path(n).stem.upper()


def _find_template_by_trigger(version: str, trigger: str) -> Optional[str]:
    base = (TEMPLATES_HL7_DIR / version).resolve()
    if not base.exists():
        return None
    want = (trigger or "").strip().upper()
    for p in base.rglob("*"):
        if p.is_file() and any(p.name.lower().endswith(ext) for ext in ALLOWED_EXTS):
            if _stem_for_match(p.name) == want:
                return p.relative_to(TEMPLATES_HL7_DIR).as_posix()
    return None


def _guess_rel_from_trigger(trigger: str, version: str) -> Optional[str]:
    """
    Find a template whose stem matches the trigger. Search the requested
    version first, then fall back to other known versions. This mirrors the
    behaviour expected by the UI where a trigger is unique across versions.
    """
    rel = _find_template_by_trigger(version, trigger)
    if rel:
        _debug_log("guess_rel.direct_hit", trigger=trigger, version=version, rel=rel)
        return rel
    for v in VALID_VERSIONS:
        if v == version:
            continue
        rel = _find_template_by_trigger(v, trigger)
        if rel:
            _debug_log("guess_rel.fallback_hit", trigger=trigger, requested=version, matched_version=v, rel=rel)
            return rel
    _debug_log("guess_rel.miss", trigger=trigger, version=version)
    return None


def generate_messages(body: dict):
    """Generate HL7 messages from a template.
    This helper takes a dict-like body and returns a FastAPI response. It is
    used by the HTTP endpoint below and by internal callers such as the
    pipeline runner."""
    _debug_log("generate_messages.start", body=body)
    start_ts = time.time()
    version = body.get("version", "hl7-v2-4")
    if version not in VALID_VERSIONS:
        raise HTTPException(400, f"Unknown version '{version}'")

    rel = (body.get("template_relpath") or "").strip()
    trig = (body.get("trigger") or "").strip()
    text = body.get("text")
    if rel and "/" not in rel:
        rel = f"{version}/{rel}"
    if not rel and trig:
        rel = _guess_rel_from_trigger(trig, version)
    if rel:
        version = rel.split("/", 1)[0]
    _debug_log("generate_messages.template_resolved", rel=rel or None, trigger=trig or None, version=version)
    if not rel and not text:
        # Note: return a helpful 404 if the trigger can’t be resolved
        raise HTTPException(404, detail=f"No template found for trigger '{trig}' in {version}")

    count = _to_int(body.get("count", 1), 1)
    if count is None or count < 1 or count > 10000:
        raise HTTPException(400, "count must be 1..10000")

    seed = body.get("seed")
    rng_seed = _to_int(seed, None)
    ensure_unique = _to_bool(body.get("ensure_unique", True))
    include_clinical = _to_bool(body.get("include_clinical", False))
    deid_input = body.get("deidentify")
    deidentify = _to_bool(deid_input)
    if count > 1 and (deid_input is None or str(deid_input).strip() == ""):
        deidentify = True
    deid_template_name = body.get("deid_template")
    deid_template = _maybe_load_deid_template(deid_template_name)
    apply_baseline = _to_bool(body.get("apply_baseline"))
    # Load text (from relpath or inline "text")
    template_path = None
    if not text:
        template_path = _assert_rel_under_templates(rel)
        template_text = load_template_text(template_path)
    else:
        template_text = text
    if template_path:
        _debug_log(
            "generate_messages.template_loaded",
            rel=rel,
            bytes=len(template_text.encode("utf-8", errors="ignore")),
        )
    else:
        _debug_log("generate_messages.inline_template", provided_bytes=len(template_text.encode("utf-8", errors="ignore")))

    msgs: list[str] = []
    for i in range(count):
        msg = template_text
        derived = None
        if rng_seed is not None:
            h = hashlib.sha256(f"{rng_seed}|{rel or 'inline'}|{i}".encode()).hexdigest()
            derived = int(h[:12], 16)

        if ensure_unique:
            msg = ensure_unique_fields(msg, index=i, seed=derived)
        if include_clinical:
            msg = enrich_clinical_fields(msg, seed=derived)
        if deidentify:
            if deid_template or apply_baseline:
                tpl_payload = deid_template or {"rules": []}
                msg = apply_deid_with_template(msg, tpl_payload, apply_baseline=apply_baseline)
            else:
                msg = deidentify_message(msg, seed=derived)
        msgs.append(msg)
    first_preview = msgs[0] if msgs else ""
    _debug_log(
        "generate_messages.done",
        messages=len(msgs),
        rel=rel or "inline",
        deidentify=deidentify,
        deid_template=deid_template_name or "",
        baseline=apply_baseline,
        ensure_unique=ensure_unique,
        include_clinical=include_clinical,
        preview=first_preview,
    )
    out = "\n".join(msgs) + ("\n" if msgs else "")
    _debug_log("generate_messages.response_ready", bytes=len(out))
    template_name = Path(rel).name if rel else "inline"
    log_activity(
        "generate",
        version=version,
        trigger=trig or "",
        count=count,
        template=template_name,
    )
    msg_id = str(uuid.uuid4())
    elapsed_ms = int((time.time() - start_ts) * 1000)
    try:
        record_event(
            {
                "stage": "generate",
                "msg_id": msg_id,
                "hl7_type": trig or "",
                "hl7_version": version,
                "status": "success",
                "elapsed_ms": elapsed_ms,
                "count": len(msgs),
                "template": template_name,
                "size_bytes": len(out.encode("utf-8", errors="ignore")),
            }
        )
    except Exception:
        logger.debug("metrics.record_event_failed", exc_info=True)
    return PlainTextResponse(out, media_type="text/plain", headers={"Cache-Control": "no-store"})

@router.post("/api/interop/generate", response_class=PlainTextResponse)
async def generate_messages_endpoint(request: Request):
    """Robust HL7 generation endpoint (JSON/form/multipart/query)."""
    _debug_log(
        "generate_messages_endpoint.invoke",
        method=request.method,
        path=request.url.path,
        query=request.url.query,
        hx=request.headers.get("hx-request"),
        accept=request.headers.get("accept"),
        referer=request.headers.get("referer"),
    )
    body = await parse_any_request(request)
    _debug_log("generate_messages_endpoint.parsed_body", body=body)
    return generate_messages(body)

@router.get("/api/interop/generate", response_class=PlainTextResponse)
async def generate_messages_get(request: Request):
    """GET variant for simple query-string based generation."""
    return await generate_messages_endpoint(request)

@router.post("/api/interop/generate/plain", response_class=PlainTextResponse)
async def generate_messages_plain(request: Request):
    _debug_log(
        "generate_messages_plain.invoke",
        method=request.method,
        path=request.url.path,
        query=request.url.query,
        hx=request.headers.get("hx-request"),
        accept=request.headers.get("accept"),
        referer=request.headers.get("referer"),
    )
    body = await parse_any_request(request)
    _debug_log("generate_messages_plain.parsed_body", body=body)
    return generate_messages(body)


async def try_generate_on_validation_error(
    request: Request, exc: RequestValidationError
):
    """Attempt to salvage legacy validation failures for /api/interop/generate."""
    path = request.url.path.rstrip("/")
    if path not in {"/api/interop/generate", "/api/interop/generate/plain"}:
        _debug_log("validation_fallback.skip_path", path=path)
        return None
    errors = exc.errors() if hasattr(exc, "errors") else []
    _debug_log("validation_fallback.recovering", path=path, errors=errors)
    try:
        body = await parse_any_request(request)
        _debug_log("validation_fallback.recovered_body", path=path, body=body)
        return generate_messages(body)
    except Exception:
        logger.exception("Failed to recover generator request after validation error")
        _debug_log("validation_fallback.failed", path=path)
        return None

def _wants_text_plain(request: Request) -> bool:
    """Return True when client prefers text/plain (or ?format=txt)."""
    accept = (request.headers.get("accept") or "").lower()
    if "text/plain" in accept:
        return True
    qs = (request.url.query or "").lower()
    return ("format=txt" in qs) or ("format=text" in qs) or ("format=plain" in qs)


def _wants_validation_html(request: Request, format_hint: Any | None = None) -> bool:
    """Detect when the caller expects an HTML validation report."""

    def _is_html(value: Any) -> bool:
        try:
            return str(value).strip().lower() == "html"
        except Exception:
            return False

    if _is_html(format_hint):
        return True

    try:
        query_format = request.query_params.get("format")  # type: ignore[attr-defined]
    except Exception:
        query_format = None
    if _is_html(query_format):
        return True

    headers = request.headers
    hx_header = headers.get("hx-request") or headers.get("HX-Request")
    if hx_header is not None:
        try:
            if str(hx_header).strip().lower() == "true":
                return True
        except Exception:
            return True
    accept = (headers.get("accept") or headers.get("Accept") or "").lower()
    return "text/html" in accept


def _normalize_validation_result(raw: Any, message_text: str) -> dict[str, Any]:
    """Map validator output into counts + issue rows for the UI report."""

    def _as_list(value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            return list(value)
        return [value]

    if not isinstance(raw, dict):
        raw = {"ok": bool(raw), "raw": raw}

    issues: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()
    ok_count = 1 if raw.get("ok") else 0
    warn_count = 0
    err_count = 0

    def append_issue(
        severity: str,
        code: str | None,
        location: str | None,
        message: str | None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        nonlocal warn_count, err_count
        sev_raw = str(severity or "info").lower()
        if "warn" in sev_raw:
            normalized = "warning"
        elif any(tag in sev_raw for tag in ("err", "fail")):
            normalized = "error"
        elif "info" in sev_raw or "ok" in sev_raw or "pass" in sev_raw:
            normalized = "ok"
        else:
            normalized = "info"
        code_text = (code or "").strip() or "—"
        raw_location = (location or "").strip()
        location_text = raw_location or "—"
        message_text_local = (message or "").strip()
        key = (normalized, code_text, location_text, message_text_local)
        if key in seen:
            return
        seen.add(key)
        if normalized == "error":
            err_count += 1
        elif normalized == "warning":
            warn_count += 1
        issues.append(
            {
                "severity": normalized,
                "code": code_text,
                "location": raw_location,
                "message": message_text_local or "—",
            }
        )
        if extra:
            issues[-1].update(extra)

    # Structured issues (already include severity/code/location/message)
    for entry in _as_list(raw.get("issues")):
        if isinstance(entry, dict):
            append_issue(
                entry.get("severity") or entry.get("level") or entry.get("status") or "info",
                entry.get("code") or entry.get("rule") or entry.get("id") or entry.get("type"),
                entry.get("location")
                or entry.get("segment")
                or entry.get("field")
                or entry.get("path")
                or entry.get("target"),
                entry.get("message") or entry.get("detail") or entry.get("description") or str(entry),
                {
                    "segment": entry.get("segment"),
                    "field": entry.get("field") or entry.get("fieldNo"),
                    "component": entry.get("component") or entry.get("component_index"),
                    "subcomponent": entry.get("subcomponent") or entry.get("subcomponent_index"),
                    "value": entry.get("value"),
                },
            )
        else:
            append_issue("info", None, None, str(entry))

    # Errors may be returned as list[str], list[dict], or dict[str, Any]
    errors = raw.get("errors")
    if isinstance(errors, dict):
        for key, value in errors.items():
            append_issue("error", str(key), None, value if isinstance(value, str) else str(value))
    else:
        for idx, entry in enumerate(_as_list(errors), start=1):
            if isinstance(entry, dict):
                append_issue(
                    entry.get("severity") or "error",
                    entry.get("code") or entry.get("rule") or f"E{idx:03}",
                    entry.get("location")
                    or entry.get("segment")
                    or entry.get("field")
                    or entry.get("path"),
                    entry.get("message") or entry.get("detail") or str(entry),
                    {
                        "segment": entry.get("segment"),
                        "field": entry.get("field") or entry.get("fieldNo"),
                        "component": entry.get("component") or entry.get("component_index"),
                        "subcomponent": entry.get("subcomponent") or entry.get("subcomponent_index"),
                        "value": entry.get("value"),
                    },
                )
            else:
                append_issue("error", f"E{idx:03}", None, str(entry))

    # Warnings mirror the error shapes
    warnings = raw.get("warnings") or raw.get("warning")
    for idx, entry in enumerate(_as_list(warnings), start=1):
        if isinstance(entry, dict):
            append_issue(
                entry.get("severity") or entry.get("level") or "warning",
                entry.get("code") or entry.get("rule") or f"W{idx:03}",
                entry.get("location")
                or entry.get("segment")
                or entry.get("field")
                or entry.get("path"),
                entry.get("message") or entry.get("detail") or str(entry),
                {
                    "segment": entry.get("segment"),
                    "field": entry.get("field") or entry.get("fieldNo"),
                    "component": entry.get("component") or entry.get("component_index"),
                    "subcomponent": entry.get("subcomponent") or entry.get("subcomponent_index"),
                    "value": entry.get("value"),
                },
            )
        else:
            append_issue("warning", f"W{idx:03}", None, str(entry))

    counts_payload = raw.get("counts")
    if isinstance(counts_payload, dict):
        try:
            ok_count = max(ok_count, int(counts_payload.get("ok") or counts_payload.get("pass") or 0))
        except Exception:
            pass
        try:
            warn_count = max(warn_count, int(counts_payload.get("warnings") or counts_payload.get("warning") or 0))
        except Exception:
            pass
        try:
            err_count = max(err_count, int(counts_payload.get("errors") or counts_payload.get("error") or 0))
        except Exception:
            pass

    if err_count == 0 and warn_count == 0:
        ok_count = max(ok_count, 1 if (message_text or raw.get("validated_message")) else ok_count)

    normalized_message = raw.get("validated_message") or raw.get("message") or message_text or ""

    return {
        "counts": {"ok": ok_count, "warnings": warn_count, "errors": err_count},
        "issues": issues,
        "validated_message": str(normalized_message or ""),
        "raw": raw,
    }


def _field_label(seg: str, idx: int) -> str:
    NAMES = {
        "PID": {
            3: "Patient Identifier List",
            5: "Patient Name",
            7: "Date/Time of Birth",
            8: "Administrative Sex",
            11: "Patient Address",
            13: "Phone Number - Home",
            18: "Patient Account Number",
        },
        "PV1": {
            2: "Patient Class",
            3: "Assigned Patient Location",
            7: "Attending Doctor",
            19: "Visit Number",
        },
        "NK1": {2: "Name", 3: "Relationship", 4: "Address", 5: "Phone"},
        "DG1": {3: "Diagnosis Code", 6: "Diagnosis Type"},
        "AL1": {3: "Allergen", 4: "Allergen Type"},
        "IN1": {3: "Insurance Plan", 4: "Insurance Company", 36: "Policy Number"},
    }
    title = NAMES.get(seg, {}).get(idx, "")
    return f"{seg}-{idx}" + (f" ({title})" if title else "")


def _summarize_hl7_changes(
    orig: str,
    deid: str,
    logic_map: dict[tuple[str, int, int, int], str] | None = None,
) -> list[dict[str, Any]]:
    """Return per-field/component/subcomponent differences between HL7 messages."""

    logic_map = logic_map or {}
    field_sep, comp_sep, _, sub_sep = _hl7_separators(orig or deid)

    def _group_lines(text: str) -> dict[str, list[str]]:
        buckets: dict[str, list[str]] = defaultdict(list)
        for line in re.split(r"\r?\n", text or ""):
            if not line.strip():
                continue
            seg = line[:3].upper()
            buckets[seg].append(line)
        return buckets

    def _logic_for(seg: str, field_no: int, comp_no: int | None, sub_no: int | None) -> str:
        key_order = [
            (seg, field_no, comp_no or 0, sub_no or 0),
            (seg, field_no, comp_no or 0, 0),
            (seg, field_no, 0, 0),
        ]
        for key in key_order:
            value = logic_map.get(key)
            if value:
                return value
        return "—"

    before_groups = _group_lines(orig)
    after_groups = _group_lines(deid)
    segments = sorted(set(before_groups) | set(after_groups))

    changes: list[dict[str, Any]] = []
    for seg in segments:
        before = before_groups.get(seg, [])
        after = after_groups.get(seg, [])
        count = max(len(before), len(after))
        for occurrence in range(count):
            before_line = before[occurrence] if occurrence < len(before) else ""
            after_line = after[occurrence] if occurrence < len(after) else ""
            if not before_line and not after_line:
                continue
            before_fields = before_line.split(field_sep) if before_line else [seg]
            after_fields = after_line.split(field_sep) if after_line else [seg]
            max_fields = max(len(before_fields), len(after_fields))
            for field_idx in range(1, max_fields):
                field_no = field_idx if seg != "MSH" else field_idx + 1
                before_field = before_fields[field_idx] if field_idx < len(before_fields) else ""
                after_field = after_fields[field_idx] if field_idx < len(after_fields) else ""
                if before_field == after_field:
                    continue
                before_components = before_field.split(comp_sep) if before_field else [""]
                after_components = after_field.split(comp_sep) if after_field else [""]
                comp_count = max(len(before_components), len(after_components)) or 1
                has_component_split = comp_count > 1 or comp_sep in before_field or comp_sep in after_field
                for comp_idx in range(comp_count):
                    component_no = comp_idx + 1
                    before_comp = before_components[comp_idx] if comp_idx < len(before_components) else ""
                    after_comp = after_components[comp_idx] if comp_idx < len(after_components) else ""
                    if sub_sep and (sub_sep in before_comp or sub_sep in after_comp):
                        before_subs = before_comp.split(sub_sep)
                        after_subs = after_comp.split(sub_sep)
                        sub_count = max(len(before_subs), len(after_subs)) or 1
                        for sub_idx in range(sub_count):
                            sub_no = sub_idx + 1
                            before_sub = before_subs[sub_idx] if sub_idx < len(before_subs) else ""
                            after_sub = after_subs[sub_idx] if sub_idx < len(after_subs) else ""
                            if before_sub == after_sub:
                                continue
                            logic = _logic_for(seg, field_no, component_no, sub_no)
                            changes.append(
                                {
                                    "segment": seg,
                                    "field": field_no,
                                    "component": component_no,
                                    "subcomponent": sub_no,
                                    "label": _field_label(seg, field_no),
                                    "before": before_sub,
                                    "after": after_sub,
                                    "logic": logic,
                                }
                            )
                    else:
                        if before_comp == after_comp:
                            continue
                        logic = _logic_for(seg, field_no, component_no if has_component_split else None, None)
                        changes.append(
                            {
                                "segment": seg,
                                "field": field_no,
                                "component": component_no if has_component_split else None,
                                "subcomponent": None,
                                "label": _field_label(seg, field_no),
                                "before": before_comp,
                                "after": after_comp,
                                "logic": logic,
                            }
                        )

                # Field-level difference where there were no component splits at all
                if not has_component_split:
                    logic = _logic_for(seg, field_no, None, None)
                    changes.append(
                        {
                            "segment": seg,
                            "field": field_no,
                            "component": None,
                            "subcomponent": None,
                            "label": _field_label(seg, field_no),
                            "before": before_field,
                            "after": after_field,
                            "logic": logic,
                        }
                    )

    # Deduplicate entries that may have been added twice for simple field differences
    deduped: dict[tuple[str, int, Optional[int], Optional[int], str, str], dict[str, Any]] = {}
    for change in changes:
        key = (
            change.get("segment") or "",
            int(change.get("field") or 0),
            change.get("component"),
            change.get("subcomponent"),
            change.get("before") or "",
            change.get("after") or "",
        )
        deduped[key] = change
    ordered = sorted(
        deduped.values(),
        key=lambda item: (
            item.get("segment") or "",
            int(item.get("field") or 0),
            item.get("component") or 0,
            item.get("subcomponent") or 0,
        ),
    )
    return ordered

def _normalize_index(value: Any) -> int:
    if value in (None, "", "—"):
        return 0
    try:
        return int(value)
    except Exception:
        digits = "".join(ch for ch in str(value) if ch.isdigit())
        try:
            return int(digits)
        except Exception:
            return 0


def _split_hl7_messages(text: str) -> list[str]:
    if not text or not str(text).strip():
        return []
    normalized = str(text).replace("\r\n", "\n").replace("\r", "\n")
    messages: list[str] = []
    current: list[str] = []
    for line in normalized.split("\n"):
        if line.startswith("MSH") and current:
            messages.append("\n".join(current).strip("\n"))
            current = [line]
        else:
            if not current and not line.strip():
                continue
            current.append(line)
    if current:
        messages.append("\n".join(current).strip("\n"))
    cleaned = [msg for msg in messages if msg and msg.strip()]
    if len(cleaned) <= 1 and "\n\n" in normalized:
        blocks = [blk.strip() for blk in re.split(r"(?:\r?\n){2,}", normalized) if blk.strip()]
        if len(blocks) > 1:
            return blocks
    return cleaned if cleaned else ([normalized.strip()] if normalized.strip() else [])


def _extract_deid_targets_from_template(template: Any) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    if not isinstance(template, dict):
        return targets
    candidate_lists: list[list[Any]] = []
    for key in ("targets", "rules", "items"):
        value = template.get(key)
        if isinstance(value, list):
            candidate_lists.append(value)
    seen: set[tuple[str, int, int, int]] = set()
    for entries in candidate_lists:
        for row in entries:
            if not isinstance(row, dict):
                continue
            seg = str(row.get("segment") or row.get("seg") or "").strip().upper()
            if not seg:
                continue
            field = _normalize_index(row.get("field") or row.get("field_no") or row.get("field_index"))
            if field <= 0:
                continue
            comp = _normalize_index(row.get("component") or row.get("component_index"))
            sub = _normalize_index(row.get("subcomponent") or row.get("subcomponent_index"))
            key = (seg, field, comp, sub)
            if key in seen:
                continue
            seen.add(key)
            logic = (
                row.get("logic")
                or row.get("label")
                or row.get("name")
                or row.get("rule")
                or "—"
            )
            targets.append(
                {
                    "segment": seg,
                    "field": field,
                    "component": comp,
                    "subcomponent": sub,
                    "logic": logic,
                }
            )
    return targets


def _deid_action_and_logic(rule: dict[str, Any]) -> tuple[str, str]:
    """Return (action, logic) labels for a de-identification rule."""
    if not isinstance(rule, dict):
        return ("—", "—")

    action_raw = (
        rule.get("action")
        or rule.get("type")
        or rule.get("op")
        or rule.get("name")
        or "—"
    )
    action = str(action_raw).strip().upper().replace("_", " ") or "—"

    logic_value: str | None = None
    for key in (
        "with",
        "value",
        "pattern",
        "format",
        "mask",
        "digits",
        "salt",
        "days",
        "offset",
        "min",
        "max",
        "prefix",
        "suffix",
        "param",
        "arg",
        "argument",
    ):
        if key in rule and rule[key] not in (None, "", []):
            value = rule[key]
            if isinstance(value, (list, tuple, set)):
                value = ", ".join(str(item) for item in value)
            logic_value = f"{key}: {value}"
            break

    return (action, logic_value or "—")


def _compute_deid_coverage(before: str, after: str) -> tuple[dict[tuple[str, int, int, int], set[int]], int]:
    coverage: dict[tuple[str, int, int, int], set[int]] = {}
    before_messages = _split_hl7_messages(before)
    after_messages = _split_hl7_messages(after)
    total = max(len(before_messages), len(after_messages))
    if total == 0:
        return coverage, 0
    for idx in range(total):
        src = before_messages[idx] if idx < len(before_messages) else ""
        dst = after_messages[idx] if idx < len(after_messages) else ""
        if not src and not dst:
            continue
        diffs = _summarize_hl7_changes(src, dst, {})
        for item in diffs:
            seg = (item.get("segment") or "").strip().upper()
            if not seg:
                continue
            field_no = _normalize_index(item.get("field"))
            if field_no <= 0:
                continue
            comp_no = _normalize_index(item.get("component"))
            sub_no = _normalize_index(item.get("subcomponent"))
            key = (seg, field_no, comp_no, sub_no)
            coverage.setdefault(key, set()).add(idx)
    return coverage, total


def _aggregate_validation_rows(
    issues: List[Dict[str, Any]] | None, total_messages: int
) -> Dict[str, Any]:
    total = max(int(total_messages or 1), 1)
    buckets: Dict[Tuple[Any, ...], int] = defaultdict(int)
    for entry in issues or []:
        sev = (entry.get("severity") or "error").lower() or "error"
        code = entry.get("code") or entry.get("rule")
        segment = entry.get("segment")
        field = entry.get("field")
        component = entry.get("component")
        subcomponent = entry.get("subcomponent")
        message = entry.get("message")
        key = (sev, code, segment, field, component, subcomponent, message)
        buckets[key] += 1

    rows: List[Dict[str, Any]] = []
    for (sev, code, segment, field, component, subcomponent, message), count in buckets.items():
        pct = int(round((count / total) * 100.0)) if total else 0
        rows.append(
            {
                "severity": sev,
                "code": code,
                "segment": segment,
                "field": field,
                "component": component,
                "subcomponent": subcomponent,
                "message": message,
                "count": count,
                "pct": pct,
            }
        )

    rows.sort(
        key=lambda row: (
            0 if row.get("severity") not in {"ok", "info"} else 1,
            row.get("segment") or "",
            row.get("field") or 0,
            row.get("code") or "",
            row.get("message") or "",
        )
    )
    return {"total": total, "rows": rows}


def _build_logic_map(raw_changes: Any) -> dict[tuple[str, int, int, int], str]:
    mapping: dict[tuple[str, int, int, int], str] = {}
    if not isinstance(raw_changes, list):
        return mapping

    def _num(value: Any) -> int:
        if value in (None, "", "—"):
            return 0
        try:
            return int(value)
        except Exception:
            text = str(value).strip()
            digits = "".join(ch for ch in text if ch.isdigit())
            return int(digits) if digits else 0

    for row in raw_changes:
        if not isinstance(row, dict):
            continue
        seg = (row.get("segment") or "").strip().upper()
        if not seg:
            continue
        field_no = _num(row.get("field"))
        if field_no == 0:
            continue
        comp_no = _num(row.get("component"))
        sub_no = _num(row.get("subcomponent"))
        logic = row.get("logic") or row.get("rule") or row.get("reason")
        if logic:
            mapping[(seg, field_no, comp_no, sub_no)] = logic
    return mapping


@router.post("/api/interop/deidentify")
async def api_deidentify(request: Request):
    """De-identify text; accept JSON, form, multipart, or query."""
    body = await parse_any_request(request)
    text = body.get("text")
    seed = body.get("seed")
    if text is None or str(text).strip() == "":
        raise HTTPException(status_code=400, detail="Missing 'text' to de-identify")
    try:
        seed_int = int(seed) if seed not in (None, "") else None
    except Exception:
        seed_int = None
    text_value = text if isinstance(text, str) else str(text)
    template = _maybe_load_deid_template(body.get("deid_template") or body.get("template"))
    apply_baseline = _to_bool(body.get("apply_baseline"))
    if template or apply_baseline:
        tpl_payload = template or {"rules": []}
        deid_result = apply_deid_with_template(text_value, tpl_payload, apply_baseline=apply_baseline)
    else:
        deid_result = deidentify_message(text_value, seed=seed_int)

    if isinstance(deid_result, dict):
        out_text = deid_result.get("text") or ""
        raw_changes = deid_result.get("changes") or []
    else:
        out_text = str(deid_result or "")
        raw_changes = []

    logic_map = _build_logic_map(raw_changes)
    changes = _summarize_hl7_changes(text_value, out_text, logic_map)
    log_activity(
        "deidentify",
        length=len(text_value),
        mode=body.get("mode") or "",
        changed=len(changes),
        template=body.get("deid_template") or "",
        baseline=apply_baseline,
    )
    if _wants_text_plain(request):
        return PlainTextResponse(
            out_text, media_type="text/plain", headers={"Cache-Control": "no-store"}
        )
    json_changes = [
        {
            "segment": c.get("segment"),
            "field": c.get("field"),
            "component": c.get("component"),
            "subcomponent": c.get("subcomponent"),
            "label": c.get("label"),
            "before": c.get("before", ""),
            "after": c.get("after", ""),
            "logic": c.get("logic"),
        }
        for c in changes
    ]
    return JSONResponse({"text": out_text, "changes": json_changes})


@router.post("/api/interop/deidentify/summary")
async def api_deidentify_summary(request: Request):
    """Return a compact coverage report (% applied per rule) for de-identification."""
    body = await parse_any_request(request)
    text = body.get("text") or ""
    after_text = (
        body.get("after_text")
        or body.get("after")
        or body.get("deidentified")
        or ""
    )
    seed = body.get("seed")
    try:
        seed_int = int(seed) if seed not in (None, "") else None
    except Exception:
        seed_int = None
    src = text if isinstance(text, str) else str(text)
    template = _maybe_load_deid_template(body.get("deid_template") or body.get("template"))
    apply_baseline = _to_bool(body.get("apply_baseline"))
    raw_changes: list[Any] = []
    if not after_text:
        if template or apply_baseline:
            tpl_payload = template or {"rules": []}
            deid_result = apply_deid_with_template(
                src, tpl_payload, apply_baseline=apply_baseline
            )
        else:
            deid_result = deidentify_message(src, seed=seed_int)

        if isinstance(deid_result, dict):
            after_text = deid_result.get("text") or ""
            raw_changes = deid_result.get("changes") or []
        else:
            after_text = str(deid_result or "")
            raw_changes = []
    else:
        changes_payload = body.get("changes") or []
        if isinstance(changes_payload, str):
            try:
                changes_payload = json.loads(changes_payload)
            except Exception:
                changes_payload = []
        if isinstance(changes_payload, list):
            raw_changes = changes_payload

    template_targets = _extract_deid_targets_from_template(template)
    logic_lookup: dict[tuple[str, int, int, int], str] = {
        (
            target["segment"],
            target["field"],
            target.get("component", 0),
            target.get("subcomponent", 0),
        ): target.get("logic") or "—"
        for target in template_targets
    }

    rule_index: dict[tuple[str, int, int, int], dict[str, Any]] = {}
    if isinstance(template, dict):
        for bucket in ("rules", "targets", "items"):
            maybe_rules = template.get(bucket)
            if not isinstance(maybe_rules, list):
                continue
            for rule in maybe_rules:
                if not isinstance(rule, dict):
                    continue
                seg = str(rule.get("segment") or rule.get("seg") or "").strip().upper()
                if not seg:
                    continue
                field_no = _normalize_index(
                    rule.get("field") or rule.get("field_no") or rule.get("field_index")
                )
                if field_no <= 0:
                    continue
                comp_no = _normalize_index(
                    rule.get("component") or rule.get("component_index")
                )
                sub_no = _normalize_index(
                    rule.get("subcomponent") or rule.get("subcomponent_index")
                )
                rule_index[(seg, field_no, comp_no, sub_no)] = rule
    logic_map = _build_logic_map(raw_changes)
    for key, value in logic_map.items():
        if value:
            logic_lookup.setdefault(key, value)

    coverage_map, total_messages = _compute_deid_coverage(src, after_text)
    keyset: Set[Tuple[str, int, int, int]] = set(coverage_map.keys())
    keyset.update(logic_lookup.keys())
    keyset.update(logic_map.keys())

    rows: list[dict[str, Any]] = []
    denominator = total_messages if total_messages else 1
    for seg, field_no, comp_no, sub_no in sorted(
        keyset, key=lambda item: (item[0], item[1], item[2], item[3])
    ):
        if not seg or field_no <= 0:
            continue
        applied = len(coverage_map.get((seg, field_no, comp_no, sub_no), set()))
        pct = round(100.0 * applied / denominator) if denominator else 0
        rule = rule_index.get((seg, field_no, comp_no, sub_no))
        action_label, rule_logic = _deid_action_and_logic(rule)
        logic_text = logic_lookup.get((seg, field_no, comp_no, sub_no), "—")
        if not logic_text or logic_text == "—":
            logic_text = rule_logic
        rows.append(
            {
                "segment": seg,
                "field": field_no,
                "component": comp_no or None,
                "subcomponent": sub_no or None,
                "action": action_label,
                "logic": logic_text or "—",
                "applied": applied,
                "total": total_messages,
                "pct": pct,
            }
        )

    accept = (request.headers.get("accept") or "").lower()
    if "text/html" in accept:
        return templates.TemplateResponse(
            "ui/interop/_deid_coverage.html",
            {"request": request, "r": {"rows": rows, "total_messages": total_messages}},
        )
    return JSONResponse(
        {
            "total_messages": total_messages,
            "rows": rows,
        }
    )


@router.post("/api/interop/validate")
async def api_validate(request: Request):
    """Validate HL7; accept JSON, form, multipart, or query."""
    body = await parse_any_request(request)
    text_value = body.get("message")
    if text_value is None:
        text_value = body.get("text") or ""
    text = text_value if isinstance(text_value, str) else str(text_value or "")
    profile = body.get("profile")
    template = _maybe_load_validation_template(body.get("val_template") or body.get("template"))
    if template:
        results = validate_with_template(text, template)
    else:
        results = validate_message(text, profile=profile)
    log_activity(
        "validate",
        version=body.get("version") or "",
        workbook=bool(body.get("workbook")),
        profile=profile or "",
        template=body.get("val_template") or "",
    )
    format_hint = body.get("format")
    model = _normalize_validation_result(results, text)
    enriched = _enrich_validate_issues(model.get("issues"), text)
    success_rows = _build_success_rows(template, enriched, text)
    combined_rows = enriched + success_rows
    counts = _count_issue_severities(combined_rows)
    model["issues"] = combined_rows
    model["passes"] = success_rows
    model["counts"] = counts
    message_count = max(len(_split_hl7_messages(text)), 1)
    model["total_messages"] = message_count
    model["summary"] = _aggregate_validation_rows(model["issues"], message_count)

    show_raw = body.get("show") or request.query_params.get("show") or "errors"
    show = str(show_raw).lower()
    if show == "ok":
        view_rows = [row for row in combined_rows if (row.get("severity") or "").lower() == "ok"]
    elif show == "warnings":
        view_rows = [row for row in combined_rows if (row.get("severity") or "").lower() == "warning"]
    elif show == "all":
        view_rows = list(combined_rows)
    else:
        view_rows = [row for row in combined_rows if (row.get("severity") or "").lower() == "error" or (row.get("severity") or "").lower() == "warning"]
        show = "errors"
    model["rows"] = view_rows
    model["show"] = show

    if _wants_validation_html(request, format_hint=format_hint):
        issues_payload = model.get("issues") or []
        total_payload = (
            model.get("total_messages")
            or model.get("msg_total")
            or model.get("total")
            or model.get("message_count")
            or 1
        )
        def _to_int(value: Any) -> int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return 0

        counts_payload = model.get("counts") or {}
        if not counts_payload:
            counts_payload = {
                "errors": sum(1 for row in issues_payload if (row.get("severity") or "").lower() == "error"),
                "ok": sum(1 for row in issues_payload if (row.get("severity") or "").lower() in ("ok", "passed")),
                "warnings": sum(1 for row in issues_payload if (row.get("severity") or "").lower() == "warning"),
            }
        else:
            counts_payload = {
                "errors": _to_int(
                    counts_payload.get("errors")
                    or counts_payload.get("error")
                    or counts_payload.get("fail")
                    or 0
                ),
                "ok": _to_int(
                    counts_payload.get("ok")
                    or counts_payload.get("pass")
                    or counts_payload.get("passed")
                    or 0
                ),
                "warnings": _to_int(
                    counts_payload.get("warnings")
                    or counts_payload.get("warning")
                    or 0
                ),
            }
        if not isinstance(counts_payload.get("errors"), int):
            counts_payload["errors"] = _to_int(counts_payload.get("errors"))
        if not isinstance(counts_payload.get("ok"), int):
            counts_payload["ok"] = _to_int(counts_payload.get("ok"))
        if not isinstance(counts_payload.get("warnings"), int):
            counts_payload["warnings"] = _to_int(counts_payload.get("warnings"))
        payload = dict(model)
        payload.update(
            {
                "issues": issues_payload,
                "counts": counts_payload,
                "total_messages": max(int(total_payload), 1),
                "raw": model.get("raw") or model,
                "validated_message": model.get("validated_message") or text,
            }
        )
        return templates.TemplateResponse(
            "ui/interop/_validate_report.html",
            {
                "request": request,
                "r": payload,
                "validate_api": str(request.url_for("api_validate")),
            },
        )
    return JSONResponse(model)


@router.post("/api/interop/mllp/send")
async def api_mllp_send(request: Request):
    """Send messages over MLLP; accept JSON, form, multipart, or query."""
    body = await parse_any_request(request)
    host = (body.get("host") or "").strip()
    port = int(body.get("port") or 0)
    timeout = float(body.get("timeout") or 5.0)
    messages = (
        body.get("messages")
        or body.get("message")
        or body.get("text")
        or ""
    )
    if not host or not port:
        raise HTTPException(status_code=400, detail="Missing 'host' or 'port'")
    if isinstance(messages, str):
        chunks = re.split(r"\r?\n\s*\r?\n", messages)
        messages_list = [m.strip() for m in chunks if m.strip()]
    elif isinstance(messages, list):
        messages_list = [str(m).strip() for m in messages if str(m).strip()]
    else:
        messages_list = []
    if not messages_list:
        raise HTTPException(status_code=400, detail="No messages parsed from input")
    acks = send_mllp_batch(host, port, messages_list, timeout=timeout)
    log_activity(
        "mllp_send",
        host=host,
        port=port,
        messages=len(messages_list),
        timeout=timeout,
    )
    return JSONResponse({"sent": len(messages_list), "acks": acks})
