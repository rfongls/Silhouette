import subprocess

def test_console_entrypoint_help():
    result = subprocess.run(
        ["python", "-m", "silhouette_core.cli", "fhir", "translate", "-h"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Translate HL7 v2 messages" in result.stdout
