import pathlib
import yaml

def test_next_phase_issues_yaml_valid():
    path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "next_phase_issues.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) == 7
    assert all("title" in issue and "body" in issue for issue in data)
