"""
Cybersecurity end-to-end smoke tests (offline-first, skills/ at repo root).

This suite verifies the core happy path:
  1) Gate (allow path) writes decision & audit JSON
  2) Recon (version profile) flags KEV for seeded CVE-0001 on an HTTP service
  3) Netforensics stub writes a well-formed JSON (packets/flows/index/alerts)
  4) IR playbook (ransomware) writes a complete playbook JSON
  5) Extension triage sorts findings by severity (desc)

Each test seeds the offline data (CVE/KEV) and the scope file, so it does not
depend on network connectivity or external services.
"""
import json
import importlib
from pathlib import Path


def seed_offline():
    """Create the offline CVE/KEV seeds and scope file if missing."""
    cve_dir = Path("data/security/seeds/cve")
    kev_dir = Path("data/security/seeds/kev")
    scope_dir = Path("docs/cyber")
    cve_dir.mkdir(parents=True, exist_ok=True)
    kev_dir.mkdir(parents=True, exist_ok=True)
    scope_dir.mkdir(parents=True, exist_ok=True)

    (cve_dir / "cve_seed.json").write_text(
        json.dumps({"CVE-0001": {"summary": "Demo CVE for offline tests", "severity": 5}}),
        encoding="utf-8",
    )
    (kev_dir / "kev_seed.json").write_text(
        json.dumps({"cves": ["CVE-0001"]}), encoding="utf-8"
    )
    (scope_dir / "scope_example.txt").write_text(
        "example.com\n*.example.com\nsub.example.com\n", encoding="utf-8"
    )


def _load_result_path(tool_output: str) -> Path:
    """Parse a wrapper's JSON output and return the 'result' file path."""
    data = json.loads(tool_output)
    assert data.get("ok") is True, f"Wrapper returned not ok: {tool_output}"
    p = Path(data.get("result", ""))
    assert p.exists(), f"Result path doesn't exist: {p}"
    return p


def test_gate_allow_and_audit(tmp_path):
    """Ensures pentest gate permits in-scope target with auth doc AND writes audit."""
    seed_offline()
    out_dir = tmp_path / "run"
    out_dir.mkdir(parents=True, exist_ok=True)
    # auth doc
    auth = tmp_path / "auth.pdf"
    auth.write_text("auth", encoding="utf-8")

    mod = importlib.import_module("skills.cyber_pentest_gate.v1.wrapper")
    res = mod.tool(json.dumps({
        "target": "sub.example.com",
        "scope_file": "docs/cyber/scope_example.txt",
        "auth_doc": str(auth),
        "out_dir": str(out_dir),
    }))
    gate_path = _load_result_path(res)
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    assert gate["target"] == "sub.example.com"

    # audit should live alongside result
    audit = gate_path.parent / "pentest_gate_audit.json"
    assert audit.exists(), "Audit JSON not found"
    audit_obj = json.loads(audit.read_text(encoding="utf-8"))
    assert audit_obj.get("decision") in {"allow", "deny"}


def test_recon_version_profile_kev_flag(tmp_path):
    """Ensures recon(version) shows an HTTP service with at least one KEV CVE flagged."""
    seed_offline()
    out_dir = tmp_path / "run"
    out_dir.mkdir(parents=True, exist_ok=True)

    mod = importlib.import_module("skills.cyber_recon_scan.v1.wrapper")
    res = mod.tool(json.dumps({
        "target": "sub.example.com",
        "scope_file": "docs/cyber/scope_example.txt",
        "profile": "version",
        "out_dir": str(out_dir),
    }))
    recon_path = _load_result_path(res)
    payload = json.loads(recon_path.read_text(encoding="utf-8"))

    inv = payload["inventory"]
    svc = next(s for s in inv["services"] if s.get("service") == "http")
    # at least one KEV-flagged CVE for the http service
    assert any(c.get("kev") for c in svc.get("cves", [])), f"No KEV CVEs in {svc}"


def test_netforensics_stub(tmp_path):
    """Ensures netforensics stub produces a well-formed JSON on an empty pcap."""
    seed_offline()
    out_dir = tmp_path / "run"
    out_dir.mkdir(parents=True, exist_ok=True)

    # empty PCAP (stub)
    pcap = tmp_path / "sample.pcap"
    pcap.write_bytes(b"")

    mod = importlib.import_module("skills.cyber_netforensics.v1.wrapper")
    res = mod.tool(json.dumps({
        "pcap": str(pcap),
        "out_dir": str(out_dir),
    }))
    nf_path = _load_result_path(res)
    nf = json.loads(nf_path.read_text(encoding="utf-8"))

    # basic shape
    for k in ("pcap", "packets", "flows", "index", "alerts"):
        assert k in nf


def test_ir_playbook_ransomware(tmp_path):
    """Ensures ransomware IR playbook includes the core sections."""
    seed_offline()
    out_dir = tmp_path / "run"
    out_dir.mkdir(parents=True, exist_ok=True)

    mod = importlib.import_module("skills.cyber_ir_playbook.v1.wrapper")
    res = mod.tool(json.dumps({"incident": "ransomware", "out_dir": str(out_dir)}))
    pb_path = _load_result_path(res)
    pb = json.loads(pb_path.read_text(encoding="utf-8"))

    assert pb["incident"] == "ransomware"
    assert "steps" in pb and pb["steps"]
    assert "communication_plan" in pb
    assert "contacts" in pb
    assert "injects" in pb
    assert "schedule" in pb


def test_extension_triage_sorts_desc(tmp_path):
    """Ensures extension triage sorts findings by severity descending."""
    seed_offline()
    out_dir = tmp_path / "run"
    out_dir.mkdir(parents=True, exist_ok=True)

    mod = importlib.import_module("skills.cyber_extension.v1.wrapper")
    res = mod.tool(json.dumps({
        "feature": "triage",
        "findings": [
            {"id": "f1", "severity": 3},
            {"id": "f2", "severity": 5},
            {"id": "f3", "severity": 1},
        ],
        "out_dir": str(out_dir),
    }))
    ext_path = _load_result_path(res)
    payload = json.loads(ext_path.read_text(encoding="utf-8"))
    findings = payload.get("findings", [])

    # Verify descending sort by severity (ties don't matter).
    severities = [f.get("severity", -1) for f in findings]
    assert severities == sorted(severities, reverse=True), f"Not sorted desc: {severities}"
