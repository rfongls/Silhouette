import zipfile

from silhouette_core.package_clone import package_clone


def test_package_clone(tmp_path):
    profile = tmp_path / "silhouette_profile.json"
    profile.write_text('{"memory": {"entries": 1}}')
    dist = tmp_path / "distillate.json"
    dist.write_text('{}')
    out = package_clone(profile, dist, version=2, output_dir=tmp_path)
    assert out.exists()
    with zipfile.ZipFile(out, "r") as zf:
        files = zf.namelist()
        assert "silhouette_profile.json" in files
        assert "edge_launcher.py" in files
