from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Optional
import re
from urllib.parse import parse_qs
import logging
from fastapi import APIRouter, Body, HTTPException, Request, Form
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
logger = logging.getLogger(__name__)

TEMPLATES_HL7_DIR = (Path(__file__).resolve().parent.parent / "templates" / "hl7").resolve()
VALID_VERSIONS = {"hl7-v2-3", "hl7-v2-4", "hl7-v2-5"}
ALLOWED_EXTS = (".hl7", ".txt", ".hl7.j2")


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


def _stem_for_match(name: str) -> str:
    n = name
    if n.lower().endswith(".j2"):
        n = n[:-3]
    for ext in (".hl7", ".txt"):
        if n.lower().endswith(ext):
            n = n[: -len(ext)]
    return Path(n).stem.upper()


def _find_template_by_trigger(version: str, trigger: str) -> Optional[str]:
    base = (TEMPLATES_HL7_DIR / version).resolve()
    if not base.exists():
        return None
    want = (trigger or "").strip().upper()
    for p in base.rglob("*"):
        if p.is_file() and any(p.name.lower().endswith(ext) for ext in ALLOWED_EXTS):
            if _stem_for_match(p.name) == want:
                return p.relative_to(TEMPLATES_HL7_DIR).as_posix()
    return None


def _guess_rel_from_trigger(trigger: str, version: str) -> Optional[str]:
    """
    Find a template whose stem matches the trigger. Search the requested
    version first, then fall back to other known versions. This mirrors the
    behaviour expected by the UI where a trigger is unique across versions.
    """
    rel = _find_template_by_trigger(version, trigger)
    if rel:
        return rel
    for v in VALID_VERSIONS:
        if v == version:
            continue
        rel = _find_template_by_trigger(v, trigger)
        if rel:
            return rel
    return None


def generate_messages(body: dict):
    """Generate HL7 messages from a template.
    This helper takes a dict-like body and returns a FastAPI response. It is
    used by the HTTP endpoint below and by internal callers such as the
    pipeline runner."""
    logger.info("generate_messages: body=%s", body)
    version = body.get("version", "hl7-v2-4")
    if version not in VALID_VERSIONS:
        raise HTTPException(400, f"Unknown version '{version}'")

    rel = (body.get("template_relpath") or "").strip()
    trig = (body.get("trigger") or "").strip()
    text = body.get("text")
    if rel and "/" not in rel:
        rel = f"{version}/{rel}"
    if not rel and trig:
        rel = _guess_rel_from_trigger(trig, version)
    if rel:
        version = rel.split("/", 1)[0]
    logger.info("resolved template: rel=%s trigger=%s version=%s", rel, trig, version)
    if not rel and not text:
        # Note: return a helpful 404 if the trigger can’t be resolved
        raise HTTPException(404, detail=f"No template found for trigger '{trig}' in {version}")

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
    # Load text (from relpath or inline "text")
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
    logger.info("generated %d message(s) from %s", len(msgs), rel or "inline text")

    out = "\n".join(msgs) + ("\n" if msgs else "")
    logger.info("returning %d HL7 bytes", len(out))
    return PlainTextResponse(out, media_type="text/plain", headers={"Cache-Control": "no-store"})

@router.post("/api/interop/generate", response_class=PlainTextResponse)
async def generate_messages_endpoint(request: Request):
    """
    Accept JSON, x-www-form-urlencoded form, raw querystring bodies, or
    query parameters with no body. Always returns plain HL7 text. This
    avoids "value is not a valid dict" when callers post forms to a
    JSON-only handler (or vice versa).
    """
    ctype = (request.headers.get("content-type") or "").lower()
    body: dict = {}
    logger.info("incoming request: content-type=%s", ctype)

    # 1) JSON
    if "application/json" in ctype:
        try:
            parsed = await request.json()
            if isinstance(parsed, dict):
                body = parsed
            else:
                logger.warning("JSON body was not dict: %s", type(parsed))
        except Exception:
            logger.warning("failed to parse JSON body", exc_info=True)
            body = {}

    # 2) Form
    if not body:
        try:
            form = await request.form()
            body = {k: form.get(k) for k in form.keys()}
            logger.info("parsed form body: keys=%s", list(body.keys()))
        except Exception:
            logger.warning("failed to parse form body", exc_info=True)
            body = {}

    # 3) Raw 'version=...&trigger=...' (e.g., text/plain)
    if not body:
        raw = await request.body()
        logger.info("raw body bytes=%r", raw[:200])
        q = parse_qs(raw.decode("utf-8", errors="ignore"))
        body = {k: v[-1] for k, v in q.items()} if q else {}
        if body:
            logger.info("parsed raw query body: %s", body)

    # 4) URL query parameters (POST /path?version=...&trigger=...)
    if not body:
        qp = request.query_params
        body = {k: qp.get(k) for k in qp.keys()}
        logger.info("parsed query params: %s", body)

    # Friendly default: auto-deidentify when generating more than one
    try:
        cnt_raw = body.get("count", 1)
        cnt = int(cnt_raw) if str(cnt_raw).strip() != "" else 1
    except Exception:
        cnt = 1
    if cnt > 1 and ("deidentify" not in body or str(body.get("deidentify", "")).strip() == ""):
        body["deidentify"] = True
    logger.info("final parsed body=%s", body)

    return generate_messages(body)

@router.post("/api/interop/generate/plain", response_class=PlainTextResponse)
async def generate_messages_plain(request: Request):
    # Stable alias for tests/tools; shares the same robust parser.
    return await generate_messages_endpoint(request)

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
