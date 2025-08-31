from click.testing import CliRunner

from silhouette_core.cli import main as cli


def test_security_group_help():
    r = CliRunner().invoke(cli, ["security", "-h"])
    assert r.exit_code == 0
    assert "Cybersecurity utilities" in r.output


def test_security_evidence_dry_run(tmp_path):
    out_dir = tmp_path / "out"
    r = CliRunner().invoke(
        cli,
        ["security", "--out", str(out_dir), "evidence", "--dry-run"],
    )
    assert r.exit_code == 0, r.output
    assert (out_dir / "evidence_stub.txt").exists()
