import pytest

from translators.transforms import (
    ts_to_date,
    ts_to_instant,
    pid3_to_identifiers,
    name_family_given,
    sex_to_gender,
    pv1_class_to_code,
    ucum_quantity,
)


def test_ts_to_date():
    assert ts_to_date("20250130") == "2025-01-30"


def test_ts_to_instant_with_offset():
    assert ts_to_instant("20250130123045-0500") == "2025-01-30T12:30:45-05:00"


def test_ts_to_instant_without_offset():
    assert ts_to_instant("20250130123045") == "2025-01-30T12:30:45Z"


def test_pid3_to_identifiers():
    ident = pid3_to_identifiers("12345^^^ACME^MR")
    assert ident["value"] == "12345"
    assert ident["system"] == "urn:id:ACME"
    assert ident["type"]["coding"][0]["code"] == "MR"


def test_name_family_given():
    name = name_family_given("Doe^Jane")
    assert name == {"family": "Doe", "given": ["Jane"]}


def test_sex_to_gender():
    assert sex_to_gender("F") == "female"
    assert sex_to_gender("X") == "unknown"


def test_pv1_class_to_code():
    coding = pv1_class_to_code("O")
    assert coding["code"] == "AMB"
    assert coding["system"].startswith("http://terminology.hl7.org/CodeSystem")


def test_ucum_quantity():
    q = ucum_quantity("5.4", "mg")
    assert q == {
        "value": 5.4,
        "unit": "mg",
        "system": "http://unitsofmeasure.org",
        "code": "mg",
    }
