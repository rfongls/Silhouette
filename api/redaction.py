"""Shared helpers for redacting sensitive data in logs."""

from __future__ import annotations

from typing import Any

__all__ = ["REDACT_KEYS", "redact"]


REDACT_KEYS = {
    "password",
    "token",
    "authorization",
    "api_key",
    "access_token",
    "refresh_token",
    "set-cookie",
    "cookie",
    "x-api-key",
    "x-auth-token",
    "x-csrf-token",
}


def redact(value: Any, *, redact_strings: bool = False) -> Any:
    """Recursively redact secrets from nested data structures."""

    if isinstance(value, dict):
        redacted: dict[Any, Any] = {}
        for key, inner in value.items():
            if key and str(key).lower() in REDACT_KEYS:
                redacted[key] = "***REDACTED***"
            else:
                redacted[key] = redact(inner, redact_strings=redact_strings)
        return redacted
    if isinstance(value, (list, tuple)):
        return [redact(item, redact_strings=redact_strings) for item in value]
    if redact_strings and isinstance(value, (bytes, bytearray, memoryview, str)):
        return "***REDACTED***"
    return value
