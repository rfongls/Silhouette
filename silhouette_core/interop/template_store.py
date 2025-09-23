"""Helpers for managing interoperability template files.

This module centralises directory discovery, JSON persistence, and
CSV import/export utilities for de-identification and validation
templates.  The UI as well as runtime pipeline endpoints rely on these
helpers so they all behave consistently.
"""

from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from typing import Any, Iterable


_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_CONFIG_ROOT = _PACKAGE_ROOT / "configs" / "interop"
DEID_DIR = _CONFIG_ROOT / "deid_templates"
VALIDATE_DIR = _CONFIG_ROOT / "validate_templates"

_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
_VALID_ACTIONS = {"redact", "mask", "hash", "replace"}


def ensure_template_dirs() -> None:
    """Create template directories if they are missing."""

    DEID_DIR.mkdir(parents=True, exist_ok=True)
    VALIDATE_DIR.mkdir(parents=True, exist_ok=True)


ensure_template_dirs()


def _sanitize_name(name: str) -> str:
    cleaned = (name or "").strip()
    if not cleaned:
        raise ValueError("Template name is required")
    if not _NAME_RE.match(cleaned):
        raise ValueError("Template name must contain only letters, numbers, dot, dash, or underscore")
    return cleaned


def _json_path(kind: str, name: str) -> Path:
    base = DEID_DIR if kind == "deid" else VALIDATE_DIR
    ensure_template_dirs()
    return base / f"{name}.json"


def list_templates(kind: str) -> list[str]:
    base = DEID_DIR if kind == "deid" else VALIDATE_DIR
    ensure_template_dirs()
    return sorted(p.stem for p in base.glob("*.json"))


def list_deid_templates() -> list[str]:
    return list_templates("deid")


def list_validation_templates() -> list[str]:
    return list_templates("validate")


def load_template(kind: str, name: str) -> dict[str, Any]:
    name = _sanitize_name(name)
    path = _json_path(kind, name)
    if not path.exists():
        raise FileNotFoundError(name)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Template JSON must be an object")
    return data


def load_deid_template(name: str) -> dict[str, Any]:
    return load_template("deid", name)


def load_validation_template(name: str) -> dict[str, Any]:
    return load_template("validate", name)


def save_template(kind: str, data: dict[str, Any], *, original_name: str | None = None) -> dict[str, Any]:
    ensure_template_dirs()
    if not isinstance(data, dict):
        raise ValueError("Template payload must be a dict")
    name = _sanitize_name(str(data.get("name", "")))
    version = (data.get("version") or "v1").strip() or "v1"
    payload = dict(data)
    payload["name"] = name
    payload["version"] = version

    if kind == "deid":
        payload["rules"] = _normalise_deid_rules(payload.get("rules"))
    else:
        payload["checks"] = _normalise_validation_checks(payload.get("checks"))

    path = _json_path(kind, name)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    if original_name and original_name != name:
        old = _json_path(kind, _sanitize_name(original_name))
        if old.exists() and old != path:
            old.unlink()

    return payload


def save_deid_template(data: dict[str, Any], *, original_name: str | None = None) -> dict[str, Any]:
    return save_template("deid", data, original_name=original_name)


def save_validation_template(data: dict[str, Any], *, original_name: str | None = None) -> dict[str, Any]:
    return save_template("validate", data, original_name=original_name)


def delete_template(kind: str, name: str) -> None:
    path = _json_path(kind, _sanitize_name(name))
    if path.exists():
        path.unlink()


def delete_deid_template(name: str) -> None:
    delete_template("deid", name)


def delete_validation_template(name: str) -> None:
    delete_template("validate", name)


def _coerce_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except Exception:
        return None


def _normalise_deid_rules(rules: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(rules, Iterable):
        return out
    for raw in rules:
        if not isinstance(raw, dict):
            continue
        segment = (raw.get("segment") or "").strip().upper()
        field = _coerce_int(raw.get("field"))
        if not segment or not field:
            continue
        component = _coerce_int(raw.get("component"))
        subcomponent = _coerce_int(raw.get("subcomponent"))
        action = (raw.get("action") or "redact").strip().lower()
        if action not in _VALID_ACTIONS:
            action = "redact"
        param = raw.get("param")
        if param in ("", None):
            param = None
        out.append(
            {
                "segment": segment,
                "field": field,
                "component": component,
                "subcomponent": subcomponent,
                "action": action,
                "param": param,
            }
        )
    return out


def _parse_allowed_values(raw: Any) -> list[str] | None:
    if raw in (None, ""):
        return None
    if isinstance(raw, (list, tuple)):
        values = [str(v).strip() for v in raw if str(v).strip()]
    else:
        parts = re.split(r"[;,]", str(raw))
        values = [p.strip() for p in parts if p.strip()]
    return values or None


def _normalise_validation_checks(checks: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(checks, Iterable):
        return out
    for raw in checks:
        if not isinstance(raw, dict):
            continue
        segment = (raw.get("segment") or "").strip().upper()
        field = _coerce_int(raw.get("field"))
        if not segment or not field:
            continue
        required = bool(raw.get("required", True))
        pattern = (raw.get("pattern") or "").strip() or None
        allowed_values = _parse_allowed_values(raw.get("allowed_values"))
        out.append(
            {
                "segment": segment,
                "field": field,
                "required": required,
                "pattern": pattern,
                "allowed_values": allowed_values,
            }
        )
    return out


def export_deid_csv(data: dict[str, Any]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=["segment", "field", "component", "subcomponent", "action", "param"],
    )
    writer.writeheader()
    for rule in _normalise_deid_rules(data.get("rules")):
        writer.writerow(
            {
                "segment": rule.get("segment", ""),
                "field": rule.get("field", ""),
                "component": rule.get("component", ""),
                "subcomponent": rule.get("subcomponent", ""),
                "action": rule.get("action", ""),
                "param": rule.get("param", "") or "",
            }
        )
    return buffer.getvalue()


def export_validation_csv(data: dict[str, Any]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=["segment", "field", "required", "pattern", "allowed_values"],
    )
    writer.writeheader()
    for chk in _normalise_validation_checks(data.get("checks")):
        allowed = chk.get("allowed_values") or []
        allowed_str = "" if not allowed else ";".join(str(v) for v in allowed)
        writer.writerow(
            {
                "segment": chk.get("segment", ""),
                "field": chk.get("field", ""),
                "required": "true" if chk.get("required") else "false",
                "pattern": chk.get("pattern", "") or "",
                "allowed_values": allowed_str,
            }
        )
    return buffer.getvalue()


def import_deid_csv(name: str, csv_text: str, *, version: str | None = None) -> dict[str, Any]:
    reader = csv.DictReader(io.StringIO(csv_text or ""))
    rules: list[dict[str, Any]] = []
    for row in reader:
        segment = (row.get("segment") or "").strip().upper()
        field = _coerce_int(row.get("field"))
        if not segment or not field:
            continue
        component = _coerce_int(row.get("component"))
        subcomponent = _coerce_int(row.get("subcomponent"))
        action = (row.get("action") or "redact").strip().lower()
        if action not in _VALID_ACTIONS:
            action = "redact"
        param = row.get("param") or None
        if param == "":
            param = None
        rules.append(
            {
                "segment": segment,
                "field": field,
                "component": component,
                "subcomponent": subcomponent,
                "action": action,
                "param": param,
            }
        )
    payload = {"name": _sanitize_name(name), "version": version or "v1", "rules": rules}
    return save_deid_template(payload, original_name=name)


def import_validation_csv(name: str, csv_text: str, *, version: str | None = None) -> dict[str, Any]:
    reader = csv.DictReader(io.StringIO(csv_text or ""))
    checks: list[dict[str, Any]] = []
    for row in reader:
        segment = (row.get("segment") or "").strip().upper()
        field = _coerce_int(row.get("field"))
        if not segment or not field:
            continue
        req_val = (row.get("required") or "true").strip().lower()
        required = req_val in {"1", "true", "yes", "on"}
        pattern = (row.get("pattern") or "").strip() or None
        allowed_raw = row.get("allowed_values") or ""
        allowed_values = _parse_allowed_values(allowed_raw)
        checks.append(
            {
                "segment": segment,
                "field": field,
                "required": required,
                "pattern": pattern,
                "allowed_values": allowed_values,
            }
        )
    payload = {"name": _sanitize_name(name), "version": version or "v1", "checks": checks}
    return save_validation_template(payload, original_name=name)

