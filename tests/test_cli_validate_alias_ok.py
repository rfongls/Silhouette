from pathlib import Path
from click.testing import CliRunner
import pytest

from silhouette_core.cli import main
from fhir.resources.encounter import Encounter


@pytest.mark.skipif(not hasattr(Encounter, "model_validate"), reason="requires fhir.resources>=7")
def test_cli_validate_accepts_alias(tmp_path: Path):
    nd = tmp_path / "ndjson"
    nd.mkdir()
    (nd / "Encounter.ndjson").write_text(
        '{"resourceType":"Encounter","status":"finished","class":{"system":"http://terminology.hl7.org/CodeSystem/v3-ActCode","code":"IMP"}}\n',
        encoding="utf-8",
    )
    r = CliRunner().invoke(main, ["fhir", "validate", "--in-dir", str(nd)])
    assert r.exit_code == 0, r.output
    assert "Preparing to validate 1 file(s)." in r.output
    assert "Validation summary: 1 passed, 0 failed." in r.output
