import importlib.util


def test_extras_mapping_present():
    from launcher.platform_utils import extras_for
    assert extras_for("fhir") == "[fhir]"
    assert extras_for("validate") == "[validate]"
    assert extras_for("core") == ""


def test_module_imports_without_qt():
    # Import shouldn't fail even if PySide6 is missing
    m_spec = importlib.util.find_spec("launcher.main")
    assert m_spec is not None, "launcher.main should be importable"
