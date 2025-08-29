import json
from pathlib import Path

from silhouette_core.pipelines import hl7_to_fhir


def _load(path: Path) -> dict:
    data = json.loads(path.read_text())
    for entry in data.get("entry", []):
        res = entry.get("resource", {})
        if res.get("resourceType") == "Provenance":
            res["recorded"] = "IGNORE"
    return data


def test_adt_snapshot(tmp_path: Path) -> None:
    hl7_to_fhir.translate(
        input_path="tests/data/hl7/adt_a01.hl7",
        map_path="maps/adt_uscore.yaml",
        rules=None,
        bundle="transaction",
        out=str(tmp_path),
    )
    actual = _load(tmp_path / "fhir" / "bundles" / "adt_a01.json")
    expected = _load(Path("tests/data/fhir/gold/adt_a01_bundle.json"))
    assert actual == expected


def test_oru_snapshot(tmp_path: Path) -> None:
    hl7_to_fhir.translate(
        input_path="tests/data/hl7/oru_r01.hl7",
        map_path="maps/oru_uscore.yaml",
        rules=None,
        bundle="transaction",
        out=str(tmp_path),
    )
    actual = _load(tmp_path / "fhir" / "bundles" / "oru_r01.json")
    expected = _load(Path("tests/data/fhir/gold/oru_r01_bundle.json"))
    assert actual == expected

