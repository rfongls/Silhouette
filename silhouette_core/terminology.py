"""Terminology lookup utilities for HL7→FHIR translation."""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

_DATA_DIR = Path(__file__).resolve().parents[1] / "terminology"


def _load_csv(filename: str):
    path = _DATA_DIR / filename
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


@lru_cache()
def _sex_map() -> Dict[str, str]:
    rows = _load_csv("sex_map.csv")
    return {r["v2"].strip().upper(): r["admin_gender"].strip() for r in rows}


@lru_cache()
def _pv1_class_map() -> Dict[str, str]:
    rows = _load_csv("pv1_class.csv")
    return {r["v2"].strip().upper(): r["act_code"].strip() for r in rows}


@lru_cache()
def _loinc_map() -> Dict[str, Dict[str, str]]:
    rows = _load_csv("loinc_map.csv")
    result: Dict[str, Dict[str, str]] = {}
    for r in rows:
        code = r.get("obx3_code", "").strip()
        result[code] = {k: v.strip() for k, v in r.items() if k != "obx3_code"}
    return result


def lookup_gender(code: str) -> Optional[str]:
    """Return FHIR administrative gender for a v2 code, or None if unknown."""
    return _sex_map().get((code or "").strip().upper())


def lookup_encounter_class(code: str) -> Optional[str]:
    """Return FHIR Encounter.class ActCode for a PV1-2 value, or None."""
    return _pv1_class_map().get((code or "").strip().upper())


def lookup_loinc(code: str) -> Optional[Dict[str, str]]:
    """Return LOINC metadata for an OBX-3 code, or None if unknown."""
    return _loinc_map().get((code or "").strip())
