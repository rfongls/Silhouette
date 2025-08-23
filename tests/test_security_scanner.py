from silhouette_core.security.scanner import scan_text


def test_scanner_detects_secrets() -> None:
    text = "AWS_ACCESS_KEY_ID=AKIA1234567890ABCD\n" \
           "token=5f2d6b3c4e1f7a8b9c0d1e2f3a4b5c6d7e8f9a0b\n"
    findings = scan_text(text, "test.txt")
    matches = [f["match"] for f in findings]
    assert any("AKIA" in m for m in matches)
    assert any("5f2d6b3c4e1f7a8b9c0d1e2f3a4b5c6d7e8f9a0b" in m for m in matches)
