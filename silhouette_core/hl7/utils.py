from __future__ import annotations

import pytest
from hl7apy.core import Message, Segment
from hl7apy.exceptions import UnsupportedVersion

from .versioning import ensure_supported_or_skip


def make_message(event: str, version: str) -> Message:
    ensure_supported_or_skip(version)
    try:
        return Message(event, version=version)
    except UnsupportedVersion:
        pytest.skip(f"hl7apy raised UnsupportedVersion for version {version}")

def make_segment(name: str, version: str) -> Segment:
    ensure_supported_or_skip(version)
    try:
        return Segment(name, version=version)
    except UnsupportedVersion:
        pytest.skip(f"hl7apy raised UnsupportedVersion for version {version}")
