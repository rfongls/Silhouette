"""Security utilities for Silhouette Core.

Re-export scanner helpers and license lists so callers can simply::

    from silhouette_core.security import scan_path
"""

from .scanner import (
    SPDX_DENYLIST,
    SPDX_WHITELIST,
    scan_path,
    scan_paths,
    scan_text,
)

__all__ = ["scan_path", "scan_paths", "scan_text", "SPDX_WHITELIST", "SPDX_DENYLIST"]
