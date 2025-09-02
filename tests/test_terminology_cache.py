import json
from pathlib import Path
from silhouette_core import terminology_service

def _write_vs(dir: Path):
    vs = {
        "resourceType": "ValueSet",
        "compose": {
            "include": [
                {"system": "http://loinc.org", "concept": [{"code": "1234-5"}]}]
        },
    }
    dir.mkdir(parents=True, exist_ok=True)
    (dir / "http_loinc_org.json").write_text(json.dumps(vs), encoding="utf-8")


def test_validate_resource_from_cache(tmp_path):
    cache = tmp_path / "vs"
    _write_vs(cache)
    obs = {
        "resourceType": "Observation",
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "1234-5"}]},
    }
    assert terminology_service.validate_resource(obs, cache_dir=str(cache))
    obs["code"]["coding"][0]["code"] = "9999-9"
    assert not terminology_service.validate_resource(obs, cache_dir=str(cache))
