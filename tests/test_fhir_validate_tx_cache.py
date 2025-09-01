import json
import subprocess
from pathlib import Path

def test_cli_uses_tx_cache(tmp_path):
    # prepare valueset cache
    vs_dir = tmp_path / "vs"
    vs_dir.mkdir()
    vs = {"resourceType": "ValueSet", "compose": {"include": [{"system": "http://loinc.org", "concept": [{"code": "1234-5"}]}]}}
    (vs_dir / "http_loinc_org.json").write_text(json.dumps(vs), encoding="utf-8")

    # NDJSON resource
    obs = {
        "resourceType": "Observation",
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "1234-5"}]},
    }
    ndjson = tmp_path / "Observation.ndjson"
    ndjson.write_text(json.dumps(obs) + "\n", encoding="utf-8")

    result = subprocess.run(
        [
            "python",
            "-m",
            "silhouette_core.cli",
            "fhir",
            "validate",
            "--in",
            str(ndjson),
            "--tx-cache",
            str(vs_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
