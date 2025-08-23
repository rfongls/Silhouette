from __future__ import annotations

import os
from collections.abc import Iterable

# hl7apy may ship without version dictionary metadata; handle gracefully.
try:  # pragma: no cover - depends on hl7apy install
    from hl7apy.consts import SUPPORTED_VERSIONS  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - fallback when const missing
    SUPPORTED_VERSIONS: tuple[str, ...] = ()

# Requested default envelope: v2.3 → v2.8 (including common minors)
REQUESTED_DEFAULT = ["2.3","2.4","2.5","2.5.1","2.6","2.7","2.7.1","2.8"]

def requested_versions_from_env(env: str | None = None) -> list[str]:
    s = env if env is not None else os.getenv("SILHOUETTE_HL7_VERSIONS", "")
    if not s:
        return REQUESTED_DEFAULT
    s = s.strip()
    if s.upper() in ("ALL", "*"):
        return list(SUPPORTED_VERSIONS)
    return [v.strip() for v in s.split(",") if v.strip()]

def effective_versions(requested: Iterable[str] | None = None) -> list[str]:
    req = list(requested) if requested is not None else requested_versions_from_env()
    sup = set(SUPPORTED_VERSIONS)
    # Keep order of req, filter to supported
    return [v for v in req if v in sup]

def ensure_supported_or_skip(version: str) -> None:
    import pytest
    if version not in SUPPORTED_VERSIONS:
        pytest.skip(
            f"HL7 version {version} not supported by hl7apy. "
            f"Supported: {sorted(SUPPORTED_VERSIONS)}"
        )
