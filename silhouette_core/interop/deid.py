from __future__ import annotations

import hashlib
import json
import random
import re
from typing import Optional

from silhouette_core.interop.deid_presets import gen_preset

try:  # pragma: no cover - optional baseline import
    from silhouette_core.interop.deid_defaults import deidentify_hl7 as _baseline_deid
except Exception:  # pragma: no cover - baseline unavailable
    _baseline_deid = None

try:  # pragma: no cover - optional dependency for better regex handling
    import regex as regex_lib  # type: ignore
except Exception:  # pragma: no cover - dependency not installed
    regex_lib = None

FIELD_SEP = "|"
COMP_SEP = "^"
SUBCOMP_SEP = "&"


def _rand_name(rng: random.Random) -> tuple[str, str]:
    first = rng.choice(["Alex", "Jordan", "Taylor", "Casey", "Morgan", "Riley", "Cameron", "Avery"])
    last = rng.choice(["Smith", "Johnson", "Lee", "Brown", "Garcia", "Davis", "Miller", "Wilson"])
    return first, last


def _set_field(line: str, idx: int, value: str) -> str:
    parts = line.rstrip("\r\n").split(FIELD_SEP)
    while len(parts) <= idx:
        parts.append("")
    parts[idx] = value
    return FIELD_SEP.join(parts)


def deidentify_message(message: str, *, seed: Optional[int] = None) -> str:
    """Lightweight, segment-aware PHI scrubbing."""
    rng = random.Random(seed if seed is not None else random.randrange(1 << 30))
    out: list[str] = []
    for ln in message.splitlines():
        if ln.startswith("PID|"):
            first, last = _rand_name(rng)
            ln = _set_field(ln, 5, f"{last}^{first}")
            ln = _set_field(ln, 13, "^^^" + str(rng.randint(200, 999)) + str(rng.randint(200, 999)) + str(rng.randint(1000, 9999)))
            ln = _set_field(ln, 11, "123 Main St^Townsville^^12345^USA")
            ln = _set_field(ln, 19, f"{rng.randint(100, 899)}-{rng.randint(10, 99)}-{rng.randint(1000, 9999)}")
        elif ln.startswith("PV1|"):
            parts = ln.split(FIELD_SEP)
            if len(parts) > 3 and parts[3]:
                comps = parts[3].split(COMP_SEP)
                if comps:
                    comps[0] = "ER"
                    parts[3] = COMP_SEP.join(comps)
                    ln = FIELD_SEP.join(parts)
        elif ln.startswith("NK1|"):
            first, last = _rand_name(rng)
            ln = _set_field(ln, 2, f"{last}^{first}")
        out.append(ln)
    return "\n".join(out)


def _read_hl7_path(
    fields: list[str],
    segment: str,
    field_idx: int,
    component_idx: int | None,
    subcomponent_idx: int | None,
) -> str:
    pos = field_idx if segment != "MSH" else field_idx - 1
    if pos < 0 or pos >= len(fields):
        return ""
    current = fields[pos] or ""
    if component_idx is None:
        return current

    comps = current.split(COMP_SEP)
    comp_pos = component_idx - 1
    if comp_pos < 0 or comp_pos >= len(comps):
        return ""
    value = comps[comp_pos] or ""
    if subcomponent_idx is None:
        return value

    subs = value.split(SUBCOMP_SEP)
    sub_pos = subcomponent_idx - 1
    if sub_pos < 0 or sub_pos >= len(subs):
        return ""
    return subs[sub_pos] or ""


def _set_hl7_path(
    fields: list[str],
    segment: str,
    field_idx: int,
    component_idx: int | None,
    subcomponent_idx: int | None,
    value: str,
) -> list[str]:
    """Write value into fields using 1-based HL7 indexing."""

    pos = field_idx if segment != "MSH" else field_idx - 1
    if pos < 0:
        return fields

    while pos >= len(fields):
        fields.append("")

    if component_idx is None:
        fields[pos] = value
        return fields

    current = fields[pos] or ""
    comps = current.split(COMP_SEP)
    comp_pos = component_idx - 1
    while comp_pos >= len(comps):
        comps.append("")

    if subcomponent_idx is None:
        comps[comp_pos] = value
        fields[pos] = COMP_SEP.join(comps)
        return fields

    subs = (comps[comp_pos] or "").split(SUBCOMP_SEP)
    sub_pos = subcomponent_idx - 1
    while sub_pos >= len(subs):
        subs.append("")
    subs[sub_pos] = value
    comps[comp_pos] = SUBCOMP_SEP.join(subs)
    fields[pos] = COMP_SEP.join(comps)
    return fields


MAX_REGEX_FIELD_LEN = 1_000_000


MAX_REGEX_FIELD_LEN = 1_000_000


def _apply_action(existing: str, action: str, param: Optional[str]) -> str:
    act = (action or "redact").strip().lower()
    if act == "redact":
        return ""
    if act == "mask":
        mask_char = (param or "*")[:1] or "*"
        return mask_char * len(existing) if existing else ""
    if act == "replace":
        return param or ""
    if act == "hash":
        salt = param or ""
        digest = hashlib.sha256((salt + (existing or "")).encode("utf-8")).hexdigest()
        return digest[:16]
    if act == "preset":
        # param is a preset key: name, birthdate, datetime, gender, address, phone, mrn, ssn, facility, note, pdf_blob, xml_blob, ...
        return gen_preset(param or "")
    if act in {"regex_replace", "regex_redact"}:
        pattern: str = ""
        repl: str = ""
        flags: str = ""
        if isinstance(param, str) and param.strip().startswith("{"):
            try:
                obj = json.loads(param)
                pattern = str(obj.get("pattern") or "")
                repl = str(obj.get("repl") or "")
                flags = str(obj.get("flags") or "").lower()
            except Exception:
                pattern = param or ""
        else:
            pattern = param or ""
        if not pattern:
            return existing or ""

        py_flags = 0
        for flag in flags:
            if flag == "i":
                py_flags |= re.IGNORECASE
            elif flag == "m":
                py_flags |= re.MULTILINE
            elif flag == "s":
                py_flags |= re.DOTALL
            elif flag == "x":
                py_flags |= re.VERBOSE

        original = existing or ""
        text = original[:MAX_REGEX_FIELD_LEN]
        remainder = "" if len(original) <= MAX_REGEX_FIELD_LEN else original[MAX_REGEX_FIELD_LEN:]

        def _mask(value: str) -> str:
            return "*" * len(value) if value else ""

        if regex_lib is not None:
            try:
                compiled = regex_lib.compile(pattern, flags=py_flags)
                if act == "regex_replace":
                    return compiled.sub(repl, text, timeout=0.05) + remainder

                def _mask_match(match):
                    span = match.group(0)
                    return _mask(span)

                return compiled.sub(_mask_match, text, timeout=0.05) + remainder
            except Exception:
                return existing or ""
        try:
            compiled_std = re.compile(pattern, py_flags)
            if act == "regex_replace":
                return compiled_std.sub(repl, text) + remainder

            def _mask_match_std(match):
                span = match.group(0)
                return _mask(span)

            return compiled_std.sub(_mask_match_std, text) + remainder
        except Exception:
            return existing or ""
    if act in {"dotnet_regex_replace", "dotnet_regex_redact"}:
        import os

        if os.environ.get("ENABLE_DOTNET_REGEX") != "1":
            return existing or ""
        # Placeholder for future sandboxed .NET regex execution
        return existing or ""
    return ""


def apply_single_rule(message_text: str, rule: dict) -> dict[str, object]:
    """Apply a single rule to an HL7 message for preview/testing purposes."""
    message_text = message_text or ""
    segment = str(rule.get("segment") or "").strip().upper()
    try:
        field_idx = int(rule.get("field") or 0)
    except Exception:
        field_idx = 0
    if not segment or field_idx <= 0:
        return {
            "before": None,
            "after": None,
            "changed": False,
            "line_before": None,
            "line_after": None,
            "message_after": message_text,
        }
    component = rule.get("component")
    if component in ("", None):
        comp_idx = None
    else:
        try:
            comp_idx = int(component)
        except Exception:
            comp_idx = None
    subcomponent = rule.get("subcomponent")
    if subcomponent in ("", None):
        sub_idx = None
    else:
        try:
            sub_idx = int(subcomponent)
        except Exception:
            sub_idx = None
    action = str(rule.get("action") or "redact").strip()
    param = rule.get("param")

    before_value: Optional[str] = None
    after_value: Optional[str] = None
    first_line_before: Optional[str] = None
    first_line_after: Optional[str] = None
    out_lines: list[str] = []

    for line in message_text.splitlines():
        parts = line.split(FIELD_SEP)
        seg_name = parts[0].strip().upper() if parts else ""
        if seg_name != segment:
            out_lines.append(line)
            continue

        existing = _read_hl7_path(parts, seg_name, field_idx, comp_idx, sub_idx)
        if before_value is None:
            before_value = existing
            first_line_before = FIELD_SEP.join(parts)

        new_value = _apply_action(existing, action, param)
        parts = _set_hl7_path(parts, seg_name, field_idx, comp_idx, sub_idx, new_value)
        out_line = FIELD_SEP.join(parts)
        if after_value is None:
            after_value = new_value
            first_line_after = out_line

        out_lines.append(out_line)

    message_after = "\n".join(out_lines) if out_lines else message_text
    changed = before_value is not None and before_value != after_value

    return {
        "before": before_value,
        "after": after_value if before_value is not None else None,
        "changed": changed,
        "line_before": first_line_before,
        "line_after": first_line_after,
        "message_after": message_after,
    }


def apply_deid_with_template(message_text: str, tpl: dict, apply_baseline: bool = False) -> str:
    """Apply a structured template to de-identify an HL7 message."""

    if not message_text:
        return message_text
    rules = (tpl or {}).get("rules") or []
    norm_rules: list[dict] = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        segment = (rule.get("segment") or "").strip().upper()
        field = rule.get("field")
        try:
            field_idx = int(field)
        except Exception:
            continue
        if not segment or field_idx <= 0:
            continue
        comp = rule.get("component")
        comp_idx = None
        if comp not in (None, ""):
            try:
                comp_idx = int(comp)
            except Exception:
                comp_idx = None
        sub = rule.get("subcomponent")
        sub_idx = None
        if sub not in (None, ""):
            try:
                sub_idx = int(sub)
            except Exception:
                sub_idx = None
        norm_rules.append(
            {
                "segment": segment,
                "field": field_idx,
                "component": comp_idx,
                "subcomponent": sub_idx,
                "action": (rule.get("action") or "redact").strip().lower(),
                "param": rule.get("param"),
            }
        )

    if not norm_rules:
        result = message_text
    else:
        out_lines: list[str] = []
        for line in message_text.splitlines():
            if not line.strip():
                out_lines.append(line)
                continue
            parts = line.split(FIELD_SEP)
            seg_name = parts[0].strip().upper() if parts else ""
            if not seg_name:
                out_lines.append(line)
                continue
            seg_rules = [r for r in norm_rules if r["segment"] == seg_name]
            if not seg_rules:
                out_lines.append(line)
                continue
            for rule in seg_rules:
                existing = _read_hl7_path(
                    parts,
                    seg_name,
                    rule["field"],
                    rule["component"],
                    rule["subcomponent"],
                )
                new_value = _apply_action(existing, rule["action"], rule.get("param"))
                parts = _set_hl7_path(
                    parts,
                    seg_name,
                    rule["field"],
                    rule["component"],
                    rule["subcomponent"],
                    new_value,
                )
            out_lines.append(FIELD_SEP.join(parts))
        result = "\n".join(out_lines)

    if apply_baseline and _baseline_deid is not None:
        from collections import defaultdict

        counts = defaultdict(set)
        return _baseline_deid(result, counts)
    return result
