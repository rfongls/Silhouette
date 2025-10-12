"""Simple transform operator for endpoint pipelines."""

from __future__ import annotations

from typing import Any


def _parse_path(path: str) -> tuple[str, int, int | None]:
    seg, rest = path.split("-", 1)
    if "." in rest:
        field, comp = rest.split(".", 1)
        return seg, int(field), int(comp)
    return seg, int(rest), None


def _get_value(document: dict[str, dict[int, str]], seg: str, field: int, comp: int | None) -> str:
    vals = document.get(seg, {})
    raw = vals.get(field)
    if raw is None:
        return ""
    if comp is None:
        return raw
    parts = raw.split("^")
    idx = comp - 1
    if 0 <= idx < len(parts):
        return parts[idx]
    return ""


def _set_value(
    document: dict[str, dict[int, str]],
    seg: str,
    field: int,
    comp: int | None,
    value: str,
) -> None:
    fields = document.setdefault(seg, {})
    if comp is None:
        fields[field] = value
        return
    raw = fields.get(field, "")
    parts = raw.split("^") if raw else []
    idx = comp - 1
    while len(parts) <= idx:
        parts.append("")
    parts[idx] = value
    fields[field] = "^".join(parts)


def parse_hl7_bytes(raw: bytes) -> dict[str, dict[int, str]]:
    text = raw.decode("utf-8", errors="replace").strip("\r\n")
    segments = [line for line in text.split("\r") if line]
    doc: dict[str, dict[int, str]] = {}
    for line in segments:
        segment = line[:3]
        rest = line[4:] if line.startswith(segment + "|") else ""
        fields = rest.split("|")
        doc.setdefault(segment, {})
        for index, value in enumerate(fields, start=1):
            doc[segment][index] = value
    return doc


def serialize_hl7(document: dict[str, dict[int, str]]) -> bytes:
    parts: list[str] = []
    for segment, field_map in document.items():
        if not field_map:
            parts.append(segment + "|")
            continue
        max_index = max(field_map.keys())
        values = [field_map.get(idx, "") for idx in range(1, max_index + 1)]
        parts.append(segment + "|" + "|".join(values))
    return ("\r".join(parts) + "\r").encode("utf-8")


class TransformOperator:
    """Apply copy/move rules to HL7 payloads."""

    def __init__(self, config: dict[str, Any]):
        self.rules = list(config.get("rules", []))

    def apply(self, message: Any) -> Any:
        if not getattr(message, "raw", None):
            return message
        document = parse_hl7_bytes(message.raw)
        for rule in self.rules:
            if "from_path" not in rule or "to_path" not in rule:
                continue
            operation = rule.get("op", "copy")
            seg_from, field_from, comp_from = _parse_path(rule["from_path"])
            seg_to, field_to, comp_to = _parse_path(rule["to_path"])
            source = _get_value(document, seg_from, field_from, comp_from)
            if operation == "move":
                _set_value(document, seg_from, field_from, comp_from, "")
            if source or operation in {"copy", "move"}:
                _set_value(document, seg_to, field_to, comp_to, source)
        message.raw = serialize_hl7(document)
        return message
