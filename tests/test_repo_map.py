from pathlib import Path

from silhouette_core.repo_map import build_repo_map


def test_build_repo_map(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "foo.py").write_text("print('hi')\n")
    files = ["src/foo.py"]
    data = build_repo_map(tmp_path, files)
    assert data["stats"]["file_count"] == 1
    assert "py" in data["detected_languages"]
