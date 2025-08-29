import json
from pathlib import Path
import json

from pathlib import Path
import json

import pytest
from click.testing import CliRunner

from silhouette_core.cli import main
from validators import hapi_cli
from silhouette_core.pipelines import hl7_to_fhir


def _write_ndjson(path: Path, resource: dict) -> None:
    path.write_text(json.dumps(resource) + "\n", encoding="utf-8")


def test_validate_cli_pass(tmp_path):
    patient = {
        "resourceType": "Patient",
        "meta": {"profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"]},
        "identifier": [{"value": "123", "system": "urn:id:HOSP"}],
        "name": [{"family": "DOE", "given": ["JOHN"]}],
        "birthDate": "1980-01-01",
        "gender": "male",
    }
    p = tmp_path / "Patient.ndjson"
    _write_ndjson(p, patient)
    runner = CliRunner()
    result = runner.invoke(main, ["fhir", "validate", "--in", str(p)])
    assert result.exit_code == 0


def test_validate_cli_fail(tmp_path):
    bad_patient = {
        "resourceType": "Patient",
        "birthDate": 123,  # invalid type
    }
    p = tmp_path / "bad.ndjson"
    _write_ndjson(p, bad_patient)
    runner = CliRunner()
    result = runner.invoke(main, ["fhir", "validate", "--in", str(p)])
    assert result.exit_code != 0
    assert "required property" in str(result.exception)


def test_hapi_cli_requires_java(monkeypatch):
    monkeypatch.delenv("JAVA_HOME", raising=False)
    with pytest.raises(RuntimeError):
        hapi_cli.run(["dummy.json"])


def test_remote_validate_helper(monkeypatch):
    called = []

    def fake_post(url, json, headers):
        called.append((url, json, headers))

        class Resp:
            def raise_for_status(self):
                return None

        return Resp()

    monkeypatch.setattr(hl7_to_fhir.requests, "post", fake_post)

    hl7_to_fhir._remote_validate("http://example.org", None, {"resourceType": "Patient"})

    assert called
    assert called[0][0] == "http://example.org/$validate"
