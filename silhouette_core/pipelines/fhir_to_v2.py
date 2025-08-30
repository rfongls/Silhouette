"""Stub renderer from FHIR bundles back to HL7 v2 messages."""
from __future__ import annotations

import json
from pathlib import Path


def render(input_path: str, map_path: str | None = None, out: str = "out/hl7") -> None:
    """Render a FHIR bundle JSON to a single HL7 v2 message.

    This is a minimal placeholder that writes a fixed MSH segment. In
    future work the mapping in ``map_path`` will drive full reverse
    rendering.
    """
    Path(out).mkdir(parents=True, exist_ok=True)
    # Read bundle to ensure path is valid; future implementation will use ``map_path``
    _ = json.loads(Path(input_path).read_text(encoding="utf-8"))
    msh = "MSH|^~\\&|SIL|SIL||||||"  # stub header
    out_path = Path(out) / (Path(input_path).stem + ".hl7")
    out_path.write_text(msh + "\r", encoding="utf-8")
