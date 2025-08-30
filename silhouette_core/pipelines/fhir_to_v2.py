"""Render FHIR bundles back to HL7 v2 messages."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def _render_patient(res: Dict[str, Any]) -> str:
    name = res.get("name", [{}])[0]
    family = name.get("family", "")
    given = name.get("given", [""])[0]
    pid_fields = [
        "PID",
        "1",
        "",
        "",
        f"{family}^{given}",
        "",
        res.get("birthDate", ""),
    ]
    return "|".join(pid_fields)


def _render_observation(res: Dict[str, Any], idx: int) -> str:
    code = (
        res.get("code", {})
        .get("coding", [{}])[0]
        .get("code", "")
    )
    value = res.get("valueQuantity", {}).get("value", "")
    fields = ["OBX", str(idx), "NM", code, "", str(value)]
    return "|".join(fields)


def render(input_path: str, map_path: str | None = None, out: str = "out/hl7") -> None:
    """Render a FHIR bundle JSON to a single HL7 v2 message.
    ``map_path`` is reserved for future detailed reverse mapping. The
    current implementation emits a very small subset of segments for
    demonstration and testing: ``MSH``, ``PID`` and ``OBX`` derived from
    ``Patient`` and ``Observation`` resources.
    """

    bundle = json.loads(Path(input_path).read_text(encoding="utf-8"))

    segments = ["MSH|^~\\&|SIL|SIL||||||"]

    entries = bundle.get("entry", [])
    obs_index = 1
    for entry in entries:
        res = entry.get("resource", {})
        rtype = res.get("resourceType")
        if rtype == "Patient":
            segments.append(_render_patient(res))
        elif rtype == "Observation":
            segments.append(_render_observation(res, obs_index))
            obs_index += 1

    hl7_message = "\r".join(segments) + "\r"

    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (Path(input_path).stem + ".hl7")
    out_path.write_text(hl7_message, encoding="utf-8")

