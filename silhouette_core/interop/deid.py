from __future__ import annotations

import hashlib
import random
from typing import Optional

try:  # pragma: no cover - optional baseline import
    from silhouette_core.interop.deid_defaults import deidentify_hl7 as _baseline_deid
except Exception:  # pragma: no cover - baseline unavailable
    _baseline_deid = None

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
    while len(fields) <= pos:
        fields.append("")
    if component_idx is None:
        fields[pos] = value
        return fields
    comps = fields[pos].split(COMP_SEP) if fields[pos] else []
    while len(comps) < component_idx:
        comps.append("")
    comp_pos = component_idx - 1
    if subcomponent_idx is None:
        comps[comp_pos] = value
    else:
        subs = comps[comp_pos].split(SUBCOMP_SEP) if comp_pos < len(comps) and comps[comp_pos] else []
        while len(subs) < subcomponent_idx:
            subs.append("")
        subs[subcomponent_idx - 1] = value
        comps[comp_pos] = SUBCOMP_SEP.join(subs)
    fields[pos] = COMP_SEP.join(comps)
    return fields


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
    if component_idx is None:
        return fields[pos]
    comps = fields[pos].split(COMP_SEP)
    comp_pos = component_idx - 1
    if comp_pos < 0 or comp_pos >= len(comps):
        return ""
    value = comps[comp_pos]
    if subcomponent_idx is None:
        return value
    subs = value.split(SUBCOMP_SEP)
    sub_pos = subcomponent_idx - 1
    if sub_pos < 0 or sub_pos >= len(subs):
        return ""
    return subs[sub_pos]


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
    return ""


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
