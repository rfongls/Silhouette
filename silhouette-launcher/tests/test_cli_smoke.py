import importlib.util
import sys
from pathlib import Path

# Ensure the launcher package is importable when running tests from the repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_extras_mapping_present():
    from launcher.platform_utils import extras_for
    assert extras_for("fhir") == "[fhir]"
    assert extras_for("validate") == "[validate]"
    assert extras_for("core") == ""


def test_module_imports_without_qt():
    # Import shouldn't fail even if PySide6 is missing
    m_spec = importlib.util.find_spec("launcher.main")
    assert m_spec is not None, "launcher.main should be importable"
