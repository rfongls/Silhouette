from __future__ import annotations

import random
from typing import Optional

FIELD_SEP = "|"
COMP_SEP = "^"


def _rand_name(rng: random.Random) -> tuple[str, str]:
    first = rng.choice(["Alex", "Jordan", "Taylor", "Casey", "Morgan", "Riley", "Cameron", "Avery"])
    last = rng.choice(["Smith", "Johnson", "Lee", "Brown", "Garcia", "Davis", "Miller", "Wilson"])
    return first, last


def _set_field(line: str, idx: int, value: str) -> str:
    parts = line.rstrip("\r\n").split(FIELD_SEP)
    while len(parts) <= idx:
        parts.append("")
    parts[idx] = value
    return FIELD_SEP.join(parts)


def deidentify_message(message: str, *, seed: Optional[int] = None) -> str:
    """Lightweight, segment-aware PHI scrubbing."""
    rng = random.Random(seed if seed is not None else random.randrange(1 << 30))
    out: list[str] = []
    for ln in message.splitlines():
        if ln.startswith("PID|"):
            first, last = _rand_name(rng)
            ln = _set_field(ln, 5, f"{last}^{first}")
            ln = _set_field(ln, 13, "^^^" + str(rng.randint(200, 999)) + str(rng.randint(200, 999)) + str(rng.randint(1000, 9999)))
            ln = _set_field(ln, 11, "123 Main St^Townsville^^12345^USA")
            ln = _set_field(ln, 19, f"{rng.randint(100, 899)}-{rng.randint(10, 99)}-{rng.randint(1000, 9999)}")
        elif ln.startswith("PV1|"):
            parts = ln.split(FIELD_SEP)
            if len(parts) > 3 and parts[3]:
                comps = parts[3].split(COMP_SEP)
                if comps:
                    comps[0] = "ER"
                    parts[3] = COMP_SEP.join(comps)
                    ln = FIELD_SEP.join(parts)
        elif ln.startswith("NK1|"):
            first, last = _rand_name(rng)
            ln = _set_field(ln, 2, f"{last}^{first}")
        out.append(ln)
    return "\n".join(out)
