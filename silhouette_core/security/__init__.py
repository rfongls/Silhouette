"""Security utilities for Silhouette Core.

This package exposes the :mod:`silhouette_core.security.scanner` helpers for
convenient imports:

.. code-block:: python

    from silhouette_core.security import scan_path
"""

from .scanner import scan_path, scan_paths, scan_text

__all__ = ["scan_path", "scan_paths", "scan_text"]

