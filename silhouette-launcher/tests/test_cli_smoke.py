def test_cli_help_loads():
    import importlib
    m = importlib.import_module("launcher.main")
    assert hasattr(m, "Launcher")
    assert "fhir" in getattr(m, "SKILLS", [])
