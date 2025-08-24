"""Security utilities for Silhouette Core.

Re-export the :mod:`scanner` helpers so callers can simply::

    from silhouette_core.security import scan_path
"""

from . import scanner
from .scanner import scan_path, scan_paths, scan_text

__all__ = ["scan_path", "scan_paths", "scan_text", "scanner"]

