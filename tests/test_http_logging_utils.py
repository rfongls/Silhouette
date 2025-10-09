from api.http_logging import _safe_json_preview


def test_safe_json_preview_redacts_secrets():
    body = b'{"Authorization":"Bearer abc123","token":"xyz","nested":{"password":"p","ok":1}}'
    preview = _safe_json_preview(body, limit=500)
    assert "***REDACTED***" in preview
    assert "abc123" not in preview
    assert "\"ok\": 1" in preview or "\"ok\":1" in preview
