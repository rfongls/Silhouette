from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Optional
import re
import json
from urllib.parse import parse_qs
from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from silhouette_core.interop.hl7_mutate import (
    enrich_clinical_fields,
    ensure_unique_fields,
    load_template_text,
)
from silhouette_core.interop.deid import deidentify_message
from silhouette_core.interop.mllp import send_mllp_batch
from silhouette_core.interop.validate_workbook import validate_message

router = APIRouter()

TEMPLATES_HL7_DIR = (Path(__file__).resolve().parent.parent / "templates" / "hl7").resolve()
VALID_VERSIONS = {"hl7-v2-3", "hl7-v2-4", "hl7-v2-5"}


def _assert_rel_under_templates(relpath: str) -> Path:
    p = (TEMPLATES_HL7_DIR / relpath).resolve()
    if not str(p).startswith(str(TEMPLATES_HL7_DIR)):
        raise HTTPException(status_code=400, detail="Invalid relpath")
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail=f"Template not found: {relpath}")
    return p


def _to_bool(v):
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    return s in ("1", "true", "on", "yes")


def _to_int(v, default=None):
    try:
        return int(v)
    except Exception:
        return default


def _derive_trigger_from_name(name: str) -> str:
    s = name
    if s.lower().endswith(".j2"):
        s = s[:-3]
    for ext in (".hl7", ".txt"):
        if s.lower().endswith(ext):
            s = s[: -len(ext)]
    return Path(s).stem.upper()


def _is_template_file(p: Path) -> bool:
    if not p.is_file():
        return False
    n = p.name.lower()
    return n.endswith(".hl7.j2") or n.endswith(".hl7") or n.endswith(".txt")


def _find_template_by_trigger(version: str, trigger: str) -> Optional[str]:
    """Return relpath under templates/hl7 for first file matching trigger, any extension."""
    base = (TEMPLATES_HL7_DIR / version).resolve()
    if not base.exists():
        return None
    want = (trigger or "").upper()
    for f in base.rglob("*"):
        if not _is_template_file(f):
            continue
        if _derive_trigger_from_name(f.name) == want:
            return f.relative_to(TEMPLATES_HL7_DIR).as_posix()
    return None


def _guess_rel_from_trigger(trigger: str, version: str) -> Optional[str]:
    """Find a template relpath for a trigger, trying the given version, then others.

    Also searches the top-level templates/hl7 directory for convenience."""
    cand = _find_template_by_trigger(version, trigger)
    if cand:
        return cand
    for v in sorted(VALID_VERSIONS):
        if v == version:
            continue
        cand = _find_template_by_trigger(v, trigger)
        if cand:
            return cand
    want = (trigger or "").upper()
    for f in TEMPLATES_HL7_DIR.iterdir():
        if _is_template_file(f) and _derive_trigger_from_name(f.name) == want:
            return f.relative_to(TEMPLATES_HL7_DIR).as_posix()
    return None


def generate_messages(body: dict):
    """Generate HL7 messages from a template.
    This helper takes a dict-like body and returns a FastAPI response. It is
    used by the HTTP endpoint below and by internal callers such as the
    pipeline runner."""
    version = body.get("version", "hl7-v2-4")
    if version not in VALID_VERSIONS:
        raise HTTPException(400, f"Unknown version '{version}'")

    rel = (body.get("template_relpath") or "").strip()
    trig = (body.get("trigger") or "").strip()
    text = body.get("text")
    if not rel and trig:
        rel = _guess_rel_from_trigger(trig, version)
    if rel:
        version = rel.split("/", 1)[0]
    if not rel and not text:
        raise HTTPException(404, f"No template found for trigger '{trig}'")

    count = _to_int(body.get("count", 1), 1)
    if count is None or count < 1 or count > 10000:
        raise HTTPException(400, "count must be 1..10000")

    seed = body.get("seed")
    rng_seed = _to_int(seed, None)
    ensure_unique = _to_bool(body.get("ensure_unique", True))
    include_clinical = _to_bool(body.get("include_clinical", False))
    deid_input = body.get("deidentify")
    deidentify = _to_bool(deid_input)
    if count > 1 and (deid_input is None or str(deid_input).strip() == ""):
        deidentify = True

    template_text = text or load_template_text(_assert_rel_under_templates(rel))

    msgs: list[str] = []
    for i in range(count):
        msg = template_text
        derived = None
        if rng_seed is not None:
            h = hashlib.sha256(f"{rng_seed}|{rel or 'inline'}|{i}".encode()).hexdigest()
            derived = int(h[:12], 16)

        if ensure_unique:
            msg = ensure_unique_fields(msg, index=i, seed=derived)
        if include_clinical:
            msg = enrich_clinical_fields(msg, seed=derived)
        if deidentify:
            msg = deidentify_message(msg, seed=derived)
        msgs.append(msg)

    out = "\n".join(msgs) + ("\n" if msgs else "")
    return PlainTextResponse(out, media_type="text/plain")

@router.post("/api/interop/generate", response_class=PlainTextResponse)
async def generate_messages_endpoint(request: Request):
    """HTTP endpoint wrapper for :func:`generate_messages`.
    Accepts JSON or HTML form posts and always returns plain HL7 text."""
    raw = await request.body()
    ctype = (request.headers.get("content-type") or "").lower()
    text = raw.decode("utf-8", errors="ignore")

    body: dict
    if "application/json" in ctype:
        try:
            parsed = json.loads(text)
            body = parsed if isinstance(parsed, dict) else {}
        except Exception:
            body = {k: v[-1] for k, v in parse_qs(text).items()}
    else:
        body = {k: v[-1] for k, v in parse_qs(text).items()}

    if not body and text.strip():
        body = {"text": text}
    return generate_messages(body)


@router.post("/api/interop/deidentify")
def api_deidentify(text: str = Body(..., embed=True), seed: Optional[int] = Body(None)):
    out = deidentify_message(text, seed=seed)
    return JSONResponse({"text": out})


@router.post("/api/interop/validate")
def api_validate(text: str = Body(..., embed=True), profile: Optional[str] = Body(None)):
    results = validate_message(text, profile=profile)
    return JSONResponse(results)


@router.post("/api/interop/mllp/send")
def api_mllp_send(
    host: str = Body(...),
    port: int = Body(...),
    messages: list[str] | str = Body(..., embed=True),
    timeout: float = Body(5.0),
):
    if isinstance(messages, str):
        chunks = re.split(r"\r?\n\s*\r?\n", messages)
        messages = [m.strip() for m in chunks if m.strip()]
        if not messages:
            raise HTTPException(status_code=400, detail="No messages parsed from input string")
    acks = send_mllp_batch(host, port, messages, timeout=timeout)
    return JSONResponse({"sent": len(messages), "acks": acks})
