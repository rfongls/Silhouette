from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Any, Optional
import re
from urllib.parse import parse_qs
import json
import logging
import os
import sys
import inspect
from fastapi import APIRouter, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from silhouette_core.interop.hl7_mutate import (
    enrich_clinical_fields,
    ensure_unique_fields,
    load_template_text,
)
from silhouette_core.interop.deid import deidentify_message
from silhouette_core.interop.mllp import send_mllp_batch
from silhouette_core.interop.validate_workbook import validate_message
from api.debug_log import log_debug_message

router = APIRouter()
logger = logging.getLogger(__name__)


def _preview(value: Any, limit: int = 160) -> str:
    """Return a short, printable preview for logging."""
    try:
        if isinstance(value, (bytes, bytearray)):
            text = value.decode("utf-8", errors="replace")
        else:
            text = str(value)
    except Exception:
        text = repr(value)
    text = text.replace("\r", "\\r").replace("\n", "\\n")
    if len(text) > limit:
        return f"{text[:limit]}…(+{len(text) - limit})"
    return text


def _debug_log(event: str, **fields: Any) -> None:
    parts = [event]
    for key, value in fields.items():
        parts.append(f"{key}={_preview(value)}")
    message = " | ".join(parts)
    if log_debug_message(message):
        logger.info(message)
        print(f"[interop_gen] {message}", file=sys.stderr, flush=True)
print("[interop_gen] robust router module imported", file=sys.stderr)
this_file = os.path.abspath(inspect.getfile(sys.modules[__name__]))
print(f"[interop_gen] using file: {this_file}", file=sys.stderr)


async def parse_any_request(request: Request) -> dict:
    """Parse JSON, x-www-form-urlencoded, multipart, or query into a dict."""
    from urllib.parse import parse_qs
    ctype = (request.headers.get("content-type") or "").lower()
    raw = await request.body()
    _debug_log(
        "parse_any_request.start",
        method=request.method,
        path=request.url.path,
        query=request.url.query,
        ctype=ctype,
        content_length=request.headers.get("content-length"),
        hx=request.headers.get("hx-request"),
        raw_preview=_preview(raw),
    )
    body: dict = {}
    # JSON
    if raw and "json" in ctype:
        try:
            parsed = json.loads(raw.decode("utf-8"))
            if isinstance(parsed, dict):
                body = parsed
        except Exception:
            body = {}
    # urlencoded or raw key=value
    if not body and raw:
        try:
            q = parse_qs(raw.decode("utf-8", errors="ignore"))
            body = {k: v[-1] for k, v in q.items()} if q else {}
        except Exception:
            body = {}
    # multipart/form-data
    if not body:
        try:
            form = await request.form()
            body = {k: form.get(k) for k in form.keys()} if form else {}
        except Exception:
            body = {}
    # query params
    if not body:
        qp = request.query_params
        body = {k: qp.get(k) for k in qp.keys()}
    # friendly default: auto-enable deidentify for batches
    try:
        cnt = int(body.get("count", 1)) if str(body.get("count", "").strip()) else 1
    except Exception:
        cnt = 1
    if cnt > 1 and ("deidentify" not in body or str(body.get("deidentify", "").strip()) == ""):
        body["deidentify"] = True
    _debug_log("parse_any_request.done", parsed_body=body)
    return body

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
        _debug_log("guess_rel.direct_hit", trigger=trigger, version=version, rel=rel)
        return rel
    for v in VALID_VERSIONS:
        if v == version:
            continue
        rel = _find_template_by_trigger(v, trigger)
        if rel:
            _debug_log("guess_rel.fallback_hit", trigger=trigger, requested=version, matched_version=v, rel=rel)
            return rel
    _debug_log("guess_rel.miss", trigger=trigger, version=version)
    return None


def generate_messages(body: dict):
    """Generate HL7 messages from a template.
    This helper takes a dict-like body and returns a FastAPI response. It is
    used by the HTTP endpoint below and by internal callers such as the
    pipeline runner."""
    _debug_log("generate_messages.start", body=body)
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
    _debug_log("generate_messages.template_resolved", rel=rel or None, trigger=trig or None, version=version)
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
    template_path = None
    if not text:
        template_path = _assert_rel_under_templates(rel)
        template_text = load_template_text(template_path)
    else:
        template_text = text
    if template_path:
        _debug_log(
            "generate_messages.template_loaded",
            rel=rel,
            bytes=len(template_text.encode("utf-8", errors="ignore")),
        )
    else:
        _debug_log("generate_messages.inline_template", provided_bytes=len(template_text.encode("utf-8", errors="ignore")))

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
    first_preview = msgs[0] if msgs else ""
    _debug_log(
        "generate_messages.done",
        messages=len(msgs),
        rel=rel or "inline",
        deidentify=deidentify,
        ensure_unique=ensure_unique,
        include_clinical=include_clinical,
        preview=first_preview,
    )
    out = "\n".join(msgs) + ("\n" if msgs else "")
    _debug_log("generate_messages.response_ready", bytes=len(out))
    return PlainTextResponse(out, media_type="text/plain", headers={"Cache-Control": "no-store"})

@router.post("/api/interop/generate", response_class=PlainTextResponse)
async def generate_messages_endpoint(request: Request):
    """Robust HL7 generation endpoint (JSON/form/multipart/query)."""
    _debug_log(
        "generate_messages_endpoint.invoke",
        method=request.method,
        path=request.url.path,
        query=request.url.query,
        hx=request.headers.get("hx-request"),
        accept=request.headers.get("accept"),
        referer=request.headers.get("referer"),
    )
    body = await parse_any_request(request)
    _debug_log("generate_messages_endpoint.parsed_body", body=body)
    return generate_messages(body)

@router.get("/api/interop/generate", response_class=PlainTextResponse)
async def generate_messages_get(request: Request):
    """GET variant for simple query-string based generation."""
    return await generate_messages_endpoint(request)

@router.post("/api/interop/generate/plain", response_class=PlainTextResponse)
async def generate_messages_plain(request: Request):
    # Stable alias for tests/tools; shares the same robust parser.
    return await generate_messages_endpoint(request)


async def try_generate_on_validation_error(
    request: Request, exc: RequestValidationError
):
    """Attempt to salvage legacy validation failures for /api/interop/generate."""
    path = request.url.path.rstrip("/")
    if path not in {"/api/interop/generate", "/api/interop/generate/plain"}:
        _debug_log("validation_fallback.skip_path", path=path)
        return None
    errors = exc.errors() if hasattr(exc, "errors") else []
    if not any(err.get("type") == "type_error.dict" for err in errors):
        _debug_log("validation_fallback.skip_error", path=path, errors=errors)
        return None
    try:
        _debug_log("validation_fallback.recovering", path=path, errors=errors)
        body = await parse_any_request(request)
        _debug_log("validation_fallback.recovered_body", path=path, body=body)
        return generate_messages(body)
    except Exception:
        logger.exception("Failed to recover generator request after validation error")
        _debug_log("validation_fallback.failed", path=path)
        return None

@router.post("/api/interop/deidentify")
async def api_deidentify(request: Request):
    """De-identify text; accept JSON, form, multipart, or query."""
    body = await parse_any_request(request)
    text = body.get("text")
    seed = body.get("seed")
    if text is None or str(text).strip() == "":
        raise HTTPException(status_code=400, detail="Missing 'text' to de-identify")
    try:
        seed_int = int(seed) if seed not in (None, "") else None
    except Exception:
        seed_int = None
    out = deidentify_message(text, seed=seed_int)
    return JSONResponse({"text": out})


@router.post("/api/interop/validate")
async def api_validate(request: Request):
    """Validate HL7; accept JSON, form, multipart, or query."""
    body = await parse_any_request(request)
    text = body.get("text", "")
    profile = body.get("profile")
    results = validate_message(text, profile=profile)
    return JSONResponse(results)


@router.post("/api/interop/mllp/send")
async def api_mllp_send(request: Request):
    """Send messages over MLLP; accept JSON, form, multipart, or query."""
    body = await parse_any_request(request)
    host = (body.get("host") or "").strip()
    port = int(body.get("port") or 0)
    timeout = float(body.get("timeout") or 5.0)
    messages = body.get("messages") or body.get("text") or ""
    if not host or not port:
        raise HTTPException(status_code=400, detail="Missing 'host' or 'port'")
    if isinstance(messages, str):
        chunks = re.split(r"\r?\n\s*\r?\n", messages)
        messages_list = [m.strip() for m in chunks if m.strip()]
    elif isinstance(messages, list):
        messages_list = [str(m).strip() for m in messages if str(m).strip()]
    else:
        messages_list = []
    if not messages_list:
        raise HTTPException(status_code=400, detail="No messages parsed from input")
    acks = send_mllp_batch(host, port, messages_list, timeout=timeout)
    return JSONResponse({"sent": len(messages_list), "acks": acks})
