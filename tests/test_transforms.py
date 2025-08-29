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
    assert ts_to_date("2025") == "2025"
    assert ts_to_date("202501") == "2025-01"
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

    ident2 = pid3_to_identifiers("45678^^^&1.2.3.4&ISO^MR")
    assert ident2["system"] == "urn:oid:1.2.3.4"
    
    ident3 = pid3_to_identifiers(" 7890 ^^ ^ ACME ^ MR ")
    assert ident3["value"] == "7890"
    assert ident3["system"] == "urn:id:ACME"


def test_name_family_given():
    name = name_family_given("Doe^Jane")
    assert name == {"family": "Doe", "given": ["Jane"]}


def test_sex_to_gender():
    assert sex_to_gender("F") == "female"
    assert sex_to_gender("f") == "female"
    assert sex_to_gender("U") == "unknown"
    assert sex_to_gender("") == "unknown"


def test_pv1_class_to_code():
    assert pv1_class_to_code("I")["code"] == "IMP"
    assert pv1_class_to_code("O")["code"] == "AMB"
    assert pv1_class_to_code("E")["code"] == "EMER"
    assert pv1_class_to_code("R")["code"] == "AMB"
    assert pv1_class_to_code("B")["code"] == "OBSENC"
    assert pv1_class_to_code("X")["code"] == "UNK"


def test_ucum_quantity():
    q = ucum_quantity("5.4", "mg")
    assert q == {
        "value": 5.4,
        "unit": "mg",
        "system": "http://unitsofmeasure.org",
        "code": "mg",
    }

    q2 = ucum_quantity(5, "mg")
    assert q2["value"] == 5.0

    q3 = ucum_quantity("5", "")
    assert q3 == {"value": 5.0, "system": "http://unitsofmeasure.org"}
