from __future__ import annotations

from datetime import datetime, timedelta
import random
from pathlib import Path
from typing import Optional

FIELD_SEP = "|"
COMP_SEP = "^"
REP_SEP = "~"
SUB_SEP = "&"


def load_template_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _set_field(line: str, field_index: int, value: str) -> str:
    parts = line.rstrip("\r\n").split(FIELD_SEP)
    while len(parts) <= field_index:
        parts.append("")
    parts[field_index] = value
    return FIELD_SEP.join(parts)


def _get_field(line: str, field_index: int) -> str:
    parts = line.rstrip("\r\n").split(FIELD_SEP)
    if field_index < len(parts):
        return parts[field_index]
    return ""


def _rand_datetime(rng: random.Random, start_days: int = -365, end_days: int = 0) -> str:
    now = datetime.utcnow()
    delta = rng.randint(start_days, end_days)
    t = now + timedelta(days=delta, seconds=rng.randint(0, 86400))
    return t.strftime("%Y%m%d%H%M%S")


def _rand_digits(rng: random.Random, n: int) -> str:
    return "".join(rng.choice("0123456789") for _ in range(n))


def _rand_alnum(rng: random.Random, n: int) -> str:
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(rng.choice(chars) for _ in range(n))


def ensure_unique_fields(message: str, *, index: int, seed: Optional[int]) -> str:
    """Make common identifiers unique across generated messages."""
    rng = random.Random(seed if seed is not None else random.randrange(1 << 30))
    lines = message.splitlines()
    out = []
    for ln in lines:
        if ln.startswith("MSH" + FIELD_SEP):
            val = f"{_rand_alnum(rng,6)}{index:06d}"
            ln = _set_field(ln, 9, val)
        elif ln.startswith("PID" + FIELD_SEP):
            cx = _get_field(ln, 3)
            comps = cx.split(COMP_SEP)
            if not comps or len(comps[0]) == 0:
                comps = ["" for _ in range(7)]
            comps[0] = _rand_digits(rng, 9)
            ln = _set_field(ln, 3, COMP_SEP.join(comps))
        elif ln.startswith("PV1" + FIELD_SEP):
            cx = _get_field(ln, 19)
            comps = cx.split(COMP_SEP)
            if not comps or len(comps[0]) == 0:
                comps = ["" for _ in range(7)]
            comps[0] = _rand_digits(rng, 8)
            ln = _set_field(ln, 19, COMP_SEP.join(comps))
        elif ln.startswith("ORC" + FIELD_SEP):
            ln = _set_field(ln, 2, _rand_alnum(rng, 10))
            ln = _set_field(ln, 3, _rand_alnum(rng, 10))
        elif ln.startswith("OBR" + FIELD_SEP):
            ln = _set_field(ln, 2, _rand_alnum(rng, 10))
            ln = _set_field(ln, 3, _rand_alnum(rng, 10))
        out.append(ln)
    return "\n".join(out)


def enrich_clinical_fields(message: str, *, seed: Optional[int]) -> str:
    """Inject basic clinical content and refresh timestamps."""
    rng = random.Random(seed if seed is not None else random.randrange(1 << 30))
    lines = message.splitlines()
    has_dg1 = any(l.startswith("DG1|") for l in lines)
    has_al1 = any(l.startswith("AL1|") for l in lines)

    out: list[str] = []
    admit_ts = _rand_datetime(rng, -180, -1)
    discharge_ts = _rand_datetime(rng, -179, 0)
    for ln in lines:
        if ln.startswith("PV1|"):
            if len(ln.split("|")) >= 46:
                ln = _set_field(ln, 44, admit_ts)
                ln = _set_field(ln, 45, discharge_ts)
        out.append(ln)

    if not has_dg1:
        code = rng.choice(["E11.9", "I10", "J06.9", "M54.5", "N39.0"])
        dg1 = f"DG1|1|ICD-10|{code}^DESC^^ICD10|||{_rand_datetime(rng,-365,-1)}||||F"
        out.append(dg1)

    if not has_al1:
        al = rng.choice([
            "AL1|1||^Penicillin||SV|RASH",
            "AL1|1||^Peanuts||SV|ANAPHYLAXIS",
            "AL1|1||^Latex||SV|URTICARIA",
        ])
        out.append(al)

    return "\n".join(out)
