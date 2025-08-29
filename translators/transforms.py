"""Helper transforms for HL7 v2 → FHIR mappings."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

_V2_IDENTIFIER_SYSTEM = "http://terminology.hl7.org/CodeSystem/v2-0203"
_V3_ACT_CODE_SYSTEM = "http://terminology.hl7.org/CodeSystem/v3-ActCode"
_UCUM_SYSTEM = "http://unitsofmeasure.org"

def ts_to_date(ts: str) -> str:
    """Convert an HL7 TS value to a FHIR date string.

    Supports precision down to the day. If only a year or year+month are
    supplied, the returned string preserves that level of precision.
    """
    if not ts:
        raise ValueError("empty timestamp")
    ts = ts.strip()
    if len(ts) >= 8:
        return datetime.strptime(ts[:8], "%Y%m%d").date().isoformat()
    if len(ts) >= 6:
        return datetime.strptime(ts[:6], "%Y%m").strftime("%Y-%m")
    if len(ts) >= 4:
        return ts[:4]
    raise ValueError("timestamp must have at least a year component")

def ts_to_instant(ts: str) -> str:
    """Convert an HL7 TS value to a FHIR instant (ISO 8601)."""
    if not ts or len(ts) < 14:
        raise ValueError("timestamp must have at least 14 digits")
    ts = ts.strip()
    dt = datetime.strptime(ts[:14], "%Y%m%d%H%M%S")
    if len(ts) >= 19 and ts[-5] in {"+", "-"}:
        sign = 1 if ts[-5] == "+" else -1
        hours = int(ts[-4:-2])
        minutes = int(ts[-2:])
        tz = timezone(sign * timedelta(hours=hours, minutes=minutes))
    else:
        tz = timezone.utc
    dt = dt.replace(tzinfo=tz)
    iso = dt.isoformat()
    return iso.replace("+00:00", "Z")

def pid3_to_identifiers(value: str) -> Dict[str, Any]:
    """Transform a PID-3 CX field into a FHIR Identifier."""
    comps = [c.strip() for c in (value or "").split("^")]
    ident: Dict[str, Any] = {
        "value": comps[0] if comps else "",
        "type": {"coding": [{"system": _V2_IDENTIFIER_SYSTEM, "code": "MR"}]},
    }
    if len(comps) > 3 and comps[3]:
        auth = comps[3].split("&")
        if len(auth) >= 3 and auth[1] and auth[2].upper() == "ISO":
            ident["system"] = f"urn:oid:{auth[1]}"
        else:
            ident["system"] = f"urn:id:{auth[0]}" if auth[0] else f"urn:id:{comps[3]}"
    return ident

def name_family_given(value: str) -> Dict[str, Any]:
    """Convert an HL7 XPN string to FHIR HumanName with family and given."""
    comps = (value or "").split("^")
    name: Dict[str, Any] = {}
    if comps and comps[0]:
        name["family"] = comps[0]
    if len(comps) > 1 and comps[1]:
        name["given"] = [comps[1]]
    return name
_SEX_MAP = {"M": "male", "F": "female", "O": "other", "U": "unknown"}

def sex_to_gender(value: str) -> str:
    """Map HL7 administrative sex codes to FHIR gender."""
    if not value:
        return "unknown"
    return _SEX_MAP.get(value.upper(), "unknown")
_PV1_CLASS_MAP = {
    "I": "IMP",
    "O": "AMB",
    "E": "EMER",
    "R": "AMB",
    "B": "OBSENC",
}

def pv1_class_to_code(value: str) -> Dict[str, str]:
    """Map PV1-2 patient class to FHIR Encounter.class coding."""
    code = _PV1_CLASS_MAP.get((value or "").upper(), "UNK")
    return {"system": _V3_ACT_CODE_SYSTEM, "code": code}

def ucum_quantity(value: str | float, unit: str, code: Optional[str] = None) -> Dict[str, Any]:
    """Create a FHIR Quantity with UCUM unit."""
    quant: Dict[str, Any] = {"value": float(value), "system": _UCUM_SYSTEM}
    if unit:
        quant["unit"] = unit
    if code or unit:
        quant["code"] = code or unit
    return quant
