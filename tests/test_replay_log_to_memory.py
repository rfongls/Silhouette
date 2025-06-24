from silhouette_core.replay_log_to_memory import parse_session_logs
from pathlib import Path


def test_parse_session_logs(tmp_path):
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "session_test.txt").write_text("[2025-01-01] USER: Hello\n")
    out = tmp_path / "memory.jsonl"
    count = parse_session_logs(logs, out)
    assert count == 1
    assert out.read_text().strip() == '{"role": "user", "content": "Hello"}'
