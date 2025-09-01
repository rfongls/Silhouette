import json
from pathlib import Path
from click.testing import CliRunner

from silhouette_core.cli import main


def write_file(p: Path, content="{}\n"):
    p.write_text(content, encoding="utf-8")


def test_validate_with_in_dir(tmp_path: Path):
    nd = tmp_path / "ndjson"
    nd.mkdir()
    write_file(nd / "Patient.ndjson")
    write_file(nd / "Encounter.ndjson")

    r = CliRunner().invoke(
        main,
        ["fhir", "validate", "--in-dir", str(nd)],
    )
    assert r.exit_code == 0
    assert "Preparing to validate 2 file(s)." in r.output


def test_validate_with_in_glob(tmp_path: Path):
    nd = tmp_path / "ndjson"
    nd.mkdir()
    write_file(nd / "Observation.ndjson")

    pattern = str(nd / "*.ndjson")
    r = CliRunner().invoke(
        main,
        ["fhir", "validate", "--in", pattern],
    )
    assert r.exit_code == 0
    assert "Preparing to validate 1 file(s)." in r.output
