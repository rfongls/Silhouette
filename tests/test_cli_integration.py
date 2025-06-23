import pexpect
import pytest

CLI = "python -m cli.main"

@pytest.fixture(autouse=True)
def cleanup(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.chdir(data_dir)
    yield

def run_cmd(cmd, expect, timeout=5):
    child = pexpect.spawn(CLI, timeout=timeout)
    child.expect(">>>")
    child.sendline(cmd)
    child.expect(expect)
    child.sendline(":exit")
    child.expect(pexpect.EOF)
    child.close()
    assert child.exitstatus == 0

def test_replay_creates_memory(tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "session_test.txt").write_text("[2025-01-01] USER: Hi\n")
    run_cmd(":replay", "Replayed 1 entries")

def test_selfcheck_reports(tmp_path):
    run_cmd(":selfcheck", "Missing required files")

def test_backup_generates_archive(tmp_path):
    run_cmd(":backup", "Backup complete")

def test_offline_mode_banner(tmp_path, monkeypatch):
    monkeypatch.setenv("SILHOUETTE_OFFLINE", "1")
    child = pexpect.spawn(CLI)
    child.expect(r"\[SAFE MODE\] Offline detected")
    child.sendline(":exit")
    child.expect(pexpect.EOF)
    assert child.exitstatus == 0
