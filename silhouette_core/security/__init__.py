"""Security utilities for Silhouette Core.

Expose scanner helpers, license lists, and the module itself so callers can::

    from silhouette_core.security import scan_path, scanner
"""

from . import scanner
from .scanner import (
    SPDX_DENYLIST,
    SPDX_WHITELIST,
    scan_path,
    scan_paths,
    scan_text,
)

__all__ = [
    "scan_path",
    "scan_paths",
    "scan_text",
    "SPDX_WHITELIST",
    "SPDX_DENYLIST",
    "scanner",
]