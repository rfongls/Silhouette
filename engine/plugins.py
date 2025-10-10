"""Import side-effect modules that register built-in engine components."""

from __future__ import annotations

# Phase 0 built-ins
from . import builtins  # noqa: F401

# Phase 0.5 / Phase 1 scaffolding
from .adapters import file as file_adapter  # noqa: F401
from .adapters import mllp as mllp_adapter  # noqa: F401
from .adapters import replay as replay_adapter  # noqa: F401
from .operators import deidentify as deidentify_operator  # noqa: F401
from .operators import validate_hl7 as validate_hl7_operator  # noqa: F401

__all__ = [
    "builtins",
    "file_adapter",
    "mllp_adapter",
    "replay_adapter",
    "deidentify_operator",
    "validate_hl7_operator",
]
