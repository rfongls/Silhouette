from importlib import import_module


def test_translators_relative_import():
    m = import_module("silhouette_core.pipelines.hl7_to_fhir")
    assert hasattr(m, "_parse_hl7")
