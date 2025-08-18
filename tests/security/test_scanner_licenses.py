import pathlib
from security.scanner import scan_path

def test_blocked_license_detected(tmp_path: pathlib.Path):
    p = tmp_path / "gpl.c"
    p.write_text("// SPDX-License-Identifier: GPL-3.0\nint main(){return 0;}\n", encoding="utf-8")
    report = scan_path(tmp_path)
    findings = report["findings"]
    assert any(f.get("category") == "license_blocked" for f in findings)


def test_nonlicensed_detected(tmp_path: pathlib.Path):
    p = tmp_path / "no_spdx.py"
    p.write_text("print('x')\n", encoding="utf-8")
    report = scan_path(tmp_path)
    findings = report["findings"]
    assert any(f.get("category") == "non_licensed" for f in findings)
