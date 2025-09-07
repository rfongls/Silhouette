from __future__ import annotations

from collections import defaultdict


def validate_message(text: str, profile: str | None = None) -> dict:
    """Placeholder validation that checks for key segments."""
    errors = defaultdict(int)
    warnings: list[str] = []
    lines = text.splitlines()
    if not any(l.startswith("MSH|") for l in lines):
        errors["Missing MSH"] += 1
    if not any(l.startswith("PID|") for l in lines):
        warnings.append("No PID segment found")
    return {"ok": len(errors) == 0, "errors": [f"{k} x{v}" for k, v in errors.items()], "warnings": warnings}
