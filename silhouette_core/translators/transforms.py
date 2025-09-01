"""Helper transforms for HL7 v2 → FHIR mappings."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
import re

from silhouette_core import terminology
from silhouette_core.identifier_registry import get_system

_V2_IDENTIFIER_SYSTEM = "http://terminology.hl7.org/CodeSystem/v2-0203"
_V3_ACT_CODE_SYSTEM = "http://terminology.hl7.org/CodeSystem/v3-ActCode"
_UCUM_SYSTEM = "http://unitsofmeasure.org"

def ts_to_date(ts: str) -> str:
    """Convert an HL7 TS value to a FHIR date string.

    Supports precision down to the day. If only a year or year+month are
    supplied, the returned string preserves that level of precision.
    """
    if not ts:
        return ""
    ts = ts.strip()
    if len(ts) >= 8:
        return datetime.strptime(ts[:8], "%Y%m%d").date().isoformat()
    if len(ts) >= 6:
        return datetime.strptime(ts[:6], "%Y%m").strftime("%Y-%m")
    if len(ts) >= 4:
        return ts[:4]
    return ""


# --- TS parsing (use dateTime when TZ unknown) ---
_TS = re.compile(r"^(?P<Y>\d{4})(?P<M>\d{2})?(?P<D>\d{2})?"
                 r"(?:(?P<h>\d{2})(?P<m>\d{2})?(?P<s>\d{2})?)?"
                 r"(?:\.(?P<frac>\d+))?(?P<tz>Z|[+-]\d{4})?$")

def ts_to_datetime(ts: str) -> str:
    m = _TS.match(ts or "")
    if not m:
        return ""
    Y, M, D = m["Y"], m["M"] or "01", m["D"] or "01"
    h, mi, s = m["h"] or "00", m["m"] or "00", m["s"] or "00"
    frac = f".{m['frac']}" if m["frac"] else ""
    tz = m["tz"]
    tz_fmt = "Z" if tz == "Z" else (f"{tz[:3]}:{tz[3:]}" if tz else "")
    return f"{Y}-{M}-{D}T{h}:{mi}:{s}{frac}{tz_fmt}"

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

def sex_to_gender(value: str, metrics: Optional[Dict[str, int]] = None) -> str:
    """Map HL7 administrative sex codes to FHIR gender.

    Increments ``metrics['tx-miss']`` when code is missing.
    """
    gender = terminology.lookup_gender(value)
    if gender:
        return gender
    if metrics is not None:
        metrics["tx-miss"] = metrics.get("tx-miss", 0) + 1
    return "unknown"

def pv1_class_to_code(value: str, metrics: Optional[Dict[str, int]] = None) -> Dict[str, str] | dict:
    """Map PV1-2 to Encounter.class; omit if unknown.

    Records a ``tx-miss`` metric when the class code is unmapped.
    """
    code = terminology.lookup_encounter_class(value)
    if code:
        return {"system": _V3_ACT_CODE_SYSTEM, "code": code}
    if metrics is not None:
        metrics["tx-miss"] = metrics.get("tx-miss", 0) + 1
    return {}

def loinc_details(code: str, metrics: Optional[Dict[str, int]] = None) -> Dict[str, str]:
    """Return LOINC metadata for an OBX-3 code or record a tx-miss."""
    row = terminology.lookup_loinc(code)
    if row:
        return row
    if metrics is not None:
        metrics["tx-miss"] = metrics.get("tx-miss", 0) + 1
    return {}

def ucum_quantity(value: str | float, unit: str, code: Optional[str] = None) -> Dict[str, Any]:
    """Create a FHIR Quantity with UCUM unit."""
    quant: Dict[str, Any] = {"value": float(value), "system": _UCUM_SYSTEM}
    if unit:
        quant["unit"] = unit
    if code or unit:
        quant["code"] = code or unit
    return quant

# ----- ORU helpers (standards-aligned) -----

def _norm_code_system(s: str) -> str:
    u = (s or "").strip()
    if u.upper() in {"LN", "LOINC"}:
        return "http://loinc.org"
    if u.upper() in {"SCT", "SNOMED"}:
        return "http://snomed.info/sct"
    if u.upper() == "CVX":
        return "http://hl7.org/fhir/sid/cvx"
    if u.upper() in {"RXNORM", "RXN"}:
        return "http://www.nlm.nih.gov/research/umls/rxnorm"
    return u

def obx_cwe_to_codeableconcept(value: str | dict) -> Dict[str, Any]:
    """Map an OBX/OBR CWE field to a FHIR CodeableConcept."""
    if isinstance(value, dict):
        code = (value.get("identifier") or "").strip()
        disp = (value.get("text") or "").strip()
        sys = _norm_code_system(value.get("system") or "")
    else:
        comps = (value or "").split("^")
        code = comps[0] if len(comps) > 0 else ""
        disp = comps[1] if len(comps) > 1 else ""
        sys = _norm_code_system(comps[2] if len(comps) > 2 else "")
    coding: Dict[str, Any] = {}
    if code:
        coding["code"] = code
    if disp:
        coding["display"] = disp
    if sys:
        coding["system"] = sys
    return {"coding": [coding]} if coding else {}


OBX11_TO_OBS_STATUS = {
    "F": "final",
    "C": "corrected",
    "P": "preliminary",
    "R": "registered",
    "D": "entered-in-error",
    "X": "cancelled",
    "U": "unknown",
}

def obx_status_to_obs_status(value: str) -> str:
    return OBX11_TO_OBS_STATUS.get((value or "").strip().upper(), "unknown")


OBR25_TO_DR_STATUS = {
    "F": "final",
    "C": "corrected",
    "P": "preliminary",
    "R": "registered",
    "X": "cancelled",
    "U": "unknown",
}

def obr_status_to_report_status(value: str) -> str:
    return OBR25_TO_DR_STATUS.get((value or "").strip().upper(), "unknown")


def default_dr_status() -> str:
    return "unknown"


def default_encounter_status() -> str:
    return "finished"


def obx_value_to_valuex(
    obx2: str,
    obx5: Any,
    obx6: dict | str | None = None,
    obx3_code: str | None = None,
    metrics: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """
    Decide Observation.value[x] from OBX-2/5(/6):
      NM/SN -> valueQuantity (UCUM from OBX-6 if present)
      CWE/CE -> valueCodeableConcept
      DT/TS -> valueDateTime
      ST/TX/FT/ID/IS -> valueString
    """
    t = (obx2 or "").strip().upper()
    if t in {"NM", "SN"}:
        uc = None
        ut = None
        if isinstance(obx6, dict):
            uc = (obx6.get("identifier") or "").strip()
            ut = (obx6.get("text") or "").strip()
        elif isinstance(obx6, str):
            parts = obx6.split("^")
            uc = parts[0] if parts else None
            ut = parts[1] if len(parts) > 1 else None
        # fallback to LOINC defaults if OBX-6 absent/empty
        if not uc or not ut:
            details = loinc_details(obx3_code or "")
            if details:
                uc = uc or details.get("default_ucum_code") or None
                ut = ut or details.get("default_unit_text") or None
            elif metrics is not None:
                # count a miss only if OBX-6 absent and no LOINC defaults
                metrics["tx-miss"] = metrics.get("tx-miss", 0) + 1
        val = float(obx5) if str(obx5).replace(".", "", 1).isdigit() else obx5
        return {"valueQuantity": ucum_quantity(val, ut or uc or "", uc or None)}
    if t in {"CWE", "CE"}:
        return {
            "valueCodeableConcept": obx_cwe_to_codeableconcept(
                obx5 if isinstance(obx5, dict) else str(obx5 or "")
            )
        }
    if t in {"DT", "TS"}:
        return {"valueDateTime": ts_to_datetime(str(obx5 or ""))}
    return {"valueString": "" if obx5 is None else str(obx5)}


def spm_cwe_to_codeableconcept(value: str | dict) -> Dict[str, Any]:
    """Map an SPM CWE field to a FHIR CodeableConcept."""
    return obx_cwe_to_codeableconcept(value)


def obs_category_laboratory() -> Dict[str, Any]:
    return {
        "coding": [
            {
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "laboratory",
            }
        ]
    }


def to_oid_uri(value: str) -> str:
    """Ensure a value is a `urn:oid:` URI."""
    v = (value or "").strip()
    if not v:
        return v
    return v if v.startswith("urn:oid:") else f"urn:oid:{v}"


# ----- Generic identifier / reference helpers -----

def cx_to_identifier(value: str) -> Dict[str, Any]:
    """Map an HL7 CX field to a FHIR Identifier."""
    comps = [c.strip() for c in (value or "").split("^")]
    ident: Dict[str, Any] = {"value": comps[0] if comps else ""}
    if len(comps) > 3 and comps[3]:
        auth = comps[3].split("&")
        if len(auth) >= 3 and auth[1] and auth[2].upper() == "ISO":
            ident["system"] = f"urn:oid:{auth[1]}"
        else:
            ident["system"] = f"urn:id:{auth[0]}" if auth[0] else f"urn:id:{comps[3]}"
    return ident


def xcn_to_identifier(value: str) -> Dict[str, Any]:
    """Map an HL7 XCN field to a Practitioner identifier."""
    comps = [c.strip() for c in (value or "").split("^")]
    ident: Dict[str, Any] = {"value": comps[0] if comps else ""}
    system = get_system("practitioner")
    if system:
        ident["system"] = system
    return ident


def xcn_to_name(value: str) -> Dict[str, Any]:
    """Extract a HumanName from an HL7 XCN field."""
    comps = [c.strip() for c in (value or "").split("^")]
    family = comps[1] if len(comps) > 1 else ""
    given = comps[2] if len(comps) > 2 else ""
    name: Dict[str, Any] = {}
    if family:
        name["family"] = family
    if given:
        name["given"] = [given]
    return name


def xcn_to_reference(value: str) -> Dict[str, Any]:
    """Map an HL7 XCN field to a FHIR Reference with identifier and display."""
    ident = xcn_to_identifier(value)
    name = xcn_to_name(value)
    ref: Dict[str, Any] = {}
    if ident:
        ref["identifier"] = ident
    if name:
        ref["display"] = " ".join(name.get("given", []) + [name.get("family", "")]).strip()
    return ref


def string_to_reference(value: str) -> Dict[str, Any]:
    """Wrap a plain string as a FHIR Reference.display."""
    val = (value or "").strip()
    return {"display": val} if val else {}


def string_to_org_identifier(value: str) -> Dict[str, Any]:
    """Convert a plain string to an Organization identifier."""
    val = (value or "").strip()
    if not val:
        return {}
    system = get_system("organization")
    ident: Dict[str, Any] = {"value": val}
    if system:
        ident["system"] = system
    return ident


def string_to_location_identifier(value: str) -> Dict[str, Any]:
    """Convert a plain string to a Location identifier."""
    val = (value or "").strip()
    if not val:
        return {}
    system = get_system("location")
    ident: Dict[str, Any] = {"value": val}
    if system:
        ident["system"] = system
    return ident


def string_to_org_reference(value: str) -> Dict[str, Any]:
    ident = string_to_org_identifier(value)
    ref: Dict[str, Any] = {}
    if ident:
        ref["identifier"] = ident
        ref["display"] = ident["value"]
    return ref


def string_to_location_reference(value: str) -> Dict[str, Any]:
    ident = string_to_location_identifier(value)
    ref: Dict[str, Any] = {}
    if ident:
        ref["identifier"] = ident
        ref["display"] = ident["value"]
    return ref


# ----- Default value helpers -----


def default_servicerequest_intent() -> str:
    return "order"


def default_participant_status() -> str:
    return "accepted"


def default_immunization_status() -> str:
    return "completed"


def default_medicationrequest_intent() -> str:
    return "order"


def default_medicationdispense_status() -> str:
    return "completed"


def default_medicationadmin_status() -> str:
    return "completed"


def default_documentreference_status() -> str:
    return "current"


def default_binary_content_type() -> str:
    return "application/octet-stream"


def default_chargeitem_status() -> str:
    return "billable"


def default_account_status() -> str:
    return "active"

# ----- Status mappers -----

_ORC_CONTROL_TO_STATUS = {
    "NW": "active",
    "OK": "active",
    "UA": "active",
    "CA": "cancelled",
    "DC": "stopped",
    "CM": "completed",
}


def orc_control_to_status(value: str) -> str:
    """Translate ORC-1 order control codes to FHIR status."""
    return _ORC_CONTROL_TO_STATUS.get((value or "").strip().upper(), "unknown")


_SCH_STATUS_TO_APPT_STATUS = {
    "BOOKED": "booked",
    "CANCELLED": "cancelled",
    "NOSHOW": "noshow",
    "FULFILLED": "fulfilled",
    "PENDING": "pending",
}

_FHIR_APPT_STATUSES = {
    "proposed",
    "pending",
    "booked",
    "arrived",
    "fulfilled",
    "cancelled",
    "noshow",
    "entered-in-error",
    "checked-in",
    "waitlist",
}


def sch_status_to_appt_status(value: str) -> str:
    """Map SCH-25 appointment status to FHIR Appointment.status."""
    key = (value or "").strip()
    if not key:
        return "proposed"
    key_upper = key.upper()
    mapped = _SCH_STATUS_TO_APPT_STATUS.get(key_upper)
    if mapped:
        return mapped
    key_lower = key.lower()
    if key_lower in _FHIR_APPT_STATUSES:
        return key_lower
    return "proposed"

_ADT_EVENT_TO_ENCOUNTER_STATUS = {
    "A02": "in-progress",
    "A03": "finished",
    "A08": "in-progress",
    "A11": "cancelled",
    "A13": "cancelled",
    "A40": "finished",
}


def adt_event_to_encounter_status(value: str) -> str:
    """Map ADT trigger events to Encounter.status."""
    return _ADT_EVENT_TO_ENCOUNTER_STATUS.get((value or "").strip().upper(), "in-progress")


def adt_event_to_patient_active(value: str) -> bool:
    """Determine Patient.active based on ADT trigger."""
    return (value or "").strip().upper() != "A40"
