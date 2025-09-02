import json
from pathlib import Path
from silhouette_core.pipelines import bulk

def test_bulk_bundle(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    data = {"resourceType": "Patient", "id": "1"}
    (src / "Patient.ndjson").write_text(
        "".join(json.dumps(data) + "\n" for _ in range(3)), encoding="utf-8"
    )
    out = tmp_path / "out"
    bulk.bundle_ndjson(str(src), str(out), batch_size=2)
    files = sorted(out.glob("batch_*.ndjson"))
    assert len(files) == 2
    assert files[0].read_text().count("\n") == 2
    assert files[1].read_text().count("\n") == 1
