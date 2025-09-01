from silhouette_core.translators.transforms import (
    sex_to_gender,
    pv1_class_to_code,
    loinc_details,
)
from silhouette_core import terminology


def test_lookup_tables():
    assert terminology.lookup_gender("F") == "female"
    assert terminology.lookup_gender("X") is None
    assert terminology.lookup_encounter_class("O") == "AMB"
    assert terminology.lookup_encounter_class("Z") is None
    loinc = terminology.lookup_loinc("789-8")
    assert loinc and loinc["default_ucum_code"] == "g/dL"
    assert terminology.lookup_loinc("0000-0") is None


def test_tx_miss_metrics():
    metrics = {}
    assert sex_to_gender("F", metrics) == "female"
    assert metrics == {}
    assert sex_to_gender("X", metrics) == "unknown"
    assert metrics["tx-miss"] == 1
    pv1_class_to_code("I", metrics)
    assert metrics["tx-miss"] == 1
    pv1_class_to_code("Z", metrics)
    assert metrics["tx-miss"] == 2
    loinc_details("789-8", metrics)
    assert metrics["tx-miss"] == 2
    loinc_details("0000-0", metrics)
    assert metrics["tx-miss"] == 3


def test_reset_cache():
    terminology.lookup_gender("F")
    terminology.reset_cache()
    assert terminology.lookup_gender("F") == "female"
