import subprocess
import sys
import shutil
import pytest
from pathlib import Path

# CLI invocation
CLI = [sys.executable, "-m", "cli.main"]

@pytest.fixture(autouse=True)
def cleanup():
    """Ensure leftover logs or memory.jsonl are removed before/after each test"""
    root = Path(__file__).parent.parent.resolve()
    for p in (root / "logs", root / "memory.jsonl"):
        if p.exists():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
    for prof in root.glob("silhouette_profile_*.json"):
        prof.unlink()
    for prof in root.glob("silhouette_profile_*.zip"):
        prof.unlink()
    yield
    for p in (root / "logs", root / "memory.jsonl"):
        if p.exists():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
    for prof in root.glob("silhouette_profile_*.json"):
        prof.unlink()
    for prof in root.glob("silhouette_profile_*.zip"):
        prof.unlink()

def run_cmd(cmd, expect):
    root = Path(__file__).parent.parent.resolve()
    proc = subprocess.run(
        CLI,
        cwd=str(root),
        input=f"{cmd}\n:exit\n",
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, f"CLI exited with {proc.returncode}, stderr: {proc.stderr}"
    assert expect in proc.stdout, f"Expected '{expect}' in output, got:\n{proc.stdout}"

def test_replay_creates_memory():
    root = Path(__file__).parent.parent.resolve()
    log_dir = root / "logs"
    log_dir.mkdir(exist_ok=True)
    (log_dir / "session_test.txt").write_text("[2025-01-01] USER: Hi\n")
    run_cmd(":replay", "Replayed 1 entries")

def test_selfcheck_reports():
    run_cmd(":selfcheck", "Missing required files")

def test_backup_generates_archive():
    run_cmd(":backup", "Backup complete")

def test_offline_mode_banner(monkeypatch):
    root = Path(__file__).parent.parent.resolve()
    monkeypatch.setenv("SILHOUETTE_OFFLINE", "1")
    result = subprocess.run(
        CLI,
        cwd=str(root),
        input=":exit\n",
        text=True,
        capture_output=True,
    )
    assert "[SAFE MODE] Offline detected" in result.stdout


def test_drift_report_command():
    run_cmd(":drift-report", "No tone drift")


def test_summary_command(tmp_path):
    root = Path(__file__).parent.parent.resolve()
    log_dir = root / "logs"
    log_dir.mkdir(exist_ok=True)
    (log_dir / "silhouette_session_test.txt").write_text("hello\n")
    run_cmd(":summary", "Session summary saved")


def test_persona_audit_command(tmp_path):
    mem = Path("memory.jsonl")
    mem.write_text('{"content": "malicious"}\n')
    persona = Path("persona.dsl")
    persona.write_text("[limits]\ndeny_on = malicious")
    run_cmd(":persona-audit", "Persona violations")
    persona.unlink()


def test_export_profile_command():
    run_cmd(":export-profile", "Profile exported")
