from silhouette_core.interop.deid import apply_deid_with_template
from silhouette_core.interop.validate_workbook import validate_with_template

SAMPLE = "MSH|^~\\&|S1|F1|R1|D1|202501011200||ADT^A01|MSGID|P|2.5\rPID|1||12345^^^HOSP^MR||DOE^JOHN||19800101|M\r"


def test_deid_redact_pid5_component1():
    tpl = {"name": "t", "rules": [{"segment": "PID", "field": 5, "component": 1, "action": "redact"}]}
    out = apply_deid_with_template(SAMPLE, tpl)
    # DOE (component 1) should be removed, but JOHN remains
    assert "DOE" not in out
    assert "JOHN" in out


def test_deid_hash_action_deterministic():
    tpl = {"name": "t", "rules": [{"segment": "MSH", "field": 10, "action": "hash", "param": "salt"}]}
    out1 = apply_deid_with_template(SAMPLE, tpl)
    out2 = apply_deid_with_template(SAMPLE, tpl)
    assert out1 == out2
    assert "MSGID" not in out1


def test_validate_required_msh9():
    tpl = {
        "name": "t",
        "checks": [
            {"segment": "MSH", "field": 9, "required": True, "pattern": "ADT\\^A01", "allowed_values": ["ADT^A01"]},
        ],
    }
    report = validate_with_template(SAMPLE, tpl)
    assert report["ok"] is True
    assert report["issues"] == []


def test_validate_bad_pattern():
    tpl = {
        "name": "t",
        "checks": [
            {"segment": "MSH", "field": 9, "required": True, "pattern": "[", "allowed_values": None},
        ],
    }
    report = validate_with_template(SAMPLE, tpl)
    assert report["ok"] is False
    assert any(issue.get("code") == "BAD_PATTERN" for issue in report.get("issues", []))
