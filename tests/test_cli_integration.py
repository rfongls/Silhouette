import subprocess
import sys
import os
import pytest
from pathlib import Path

CLI = [sys.executable, "-m", "cli.main"]

@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    # Run each test in a fresh temp directory
    monkeypatch.chdir(tmp_path)
    yield

def run_cmd(cmd, expect):
    # Launch CLI, feed it commands via stdin, capture stdout
    proc = subprocess.run(
        CLI,
        input=f"{cmd}\n:exit\n",
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, f"CLI exited with {proc.returncode}, stderr: {proc.stderr}"
    assert expect in proc.stdout, f"Expected '{expect}' in output, got:\n{proc.stdout}"

def test_replay_creates_memory(tmp_path):
    # Set up a fake session log
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "session_test.txt").write_text("[2025-01-01] USER: Hi\n")
    run_cmd(":replay", "Replayed 1 entries")

def test_selfcheck_reports(tmp_path):
    # No persona.dsl or memory.jsonl → missing
    run_cmd(":selfcheck", "Missing required files")

def test_backup_generates_archive(tmp_path):
    # Assuming export_state writes 'archive.zip' by default
    run_cmd(":backup", "Backup complete")

def test_offline_mode_banner(tmp_path, monkeypatch):
    monkeypatch.setenv("SILHOUETTE_OFFLINE", "1")
    result = subprocess.run(
        CLI,
        input=":exit\n",
        text=True,
        capture_output=True,
    )
    assert "[SAFE MODE] Offline detected" in result.stdout
