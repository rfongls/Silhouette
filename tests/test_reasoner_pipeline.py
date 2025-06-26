import json

from silhouette_core.merge_teacher_outputs import merge_teacher_outputs
from evaluate_student import load_model, run_tests


def test_merge_teacher_outputs(tmp_path):
    inp = tmp_path / "teacher.jsonl"
    out = tmp_path / "out.jsonl"
    lines = [
        json.dumps({"prompt": "p1", "teachers": {"a": "x=1", "b": "x=1"}}),
        json.dumps({"prompt": "p2", "teachers": {"a": "bad code", "b": "y=2"}}),
        json.dumps({"prompt": "p3", "teachers": {"a": "bad", "b": "also bad"}}),
    ]
    inp.write_text("\n".join(lines))
    merge_teacher_outputs(inp, out)
    data = [json.loads(line) for line in out.read_text().splitlines()]
    assert data[0]["completion"] == "x=1"
    assert data[1]["completion"] == "y=2"
    assert data[2]["completion"] == "bad"


def test_evaluate_student(tmp_path):
    adapter = tmp_path / "adapter"
    adapter.mkdir()
    model = load_model(adapter)
    tests = [{"prompt": "hi", "reference": ""}]
    compile_rate, test_rate, _ = run_tests(model, tests)
    assert 0 <= compile_rate <= 1
    assert 0 <= test_rate <= 1
