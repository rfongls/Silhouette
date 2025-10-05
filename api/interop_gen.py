from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Any, Optional
import re
from urllib.parse import parse_qs
import json
import logging
import time
import uuid
import os
import sys
import inspect
from fastapi import APIRouter, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.datastructures import UploadFile
from silhouette_core.interop.hl7_mutate import (
    enrich_clinical_fields,
    ensure_unique_fields,
    load_template_text,
)
from silhouette_core.interop.deid import deidentify_message, apply_deid_with_template
from silhouette_core.interop.mllp import send_mllp_batch
from silhouette_core.interop.validate_workbook import validate_message, validate_with_template
from api.activity_log import log_activity
from api.debug_log import log_debug_message
from api.metrics import record_event

router = APIRouter()
logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="templates")
templates.env.filters["split"] = lambda s, sep=" ", maxsplit=-1: ("" if s is None else str(s)).split(sep, maxsplit)

DEID_DIR = Path("configs/interop/deid_templates")
VAL_DIR = Path("configs/interop/validate_templates")
for folder in (DEID_DIR, VAL_DIR):
    folder.mkdir(parents=True, exist_ok=True)


def _load_template(path: Path, name: str, kind: str) -> dict:
    target = path / f"{name}.json"
    if not target.exists():
        raise HTTPException(status_code=400, detail=f"{kind.title()} template '{name}' not found")
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - malformed template
        raise HTTPException(status_code=400, detail=f"Invalid {kind} template JSON: {exc}") from exc


def load_deid_template(name: str) -> dict:
    return _load_template(DEID_DIR, name, "de-identify")


def load_validation_template(name: str) -> dict:
    return _load_template(VAL_DIR, name, "validation")


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


def _coerce_scalar(value: Any) -> Any:
    """Return a scalar when lists only contain a single value."""
    if isinstance(value, list) and len(value) == 1:
        return value[0]
    return value


def _maybe_load_deid_template(name: Any) -> dict | None:
    if not name:
        return None
    normalized = str(name).strip()
    if not normalized or normalized.lower() in {"builtin", "legacy", "none"}:
        return None
    return load_deid_template(normalized)
  

def _maybe_load_validation_template(name: Any) -> dict | None:
    if not name:
        return None
    normalized = str(name).strip()
    if not normalized or normalized.lower() in {"builtin", "legacy", "none"}:
        return None
    return load_validation_template(normalized)


_ISSUE_VALUE_PATTERNS = (
    re.compile(r"[Vv]alue ['\"]([^'\"]+)['\"]"),
    re.compile(r"got ['\"]([^'\"]+)['\"]"),
    re.compile(r"was ['\"]([^'\"]+)['\"]"),
)


def _parse_hl7_location(loc: Any):
    """Return (segment, field, component, subcomponent) parsed from an HL7 location string."""
    if loc in (None, "", "—"):
        return None, None, None, None
    text = str(loc).strip()
    if not text or text == "—":
        return None, None, None, None
    if "-" in text:
        segment, rest = text.split("-", 1)
    else:
        segment, rest = text, ""
    field = component = subcomponent = None
    if rest:
        rest = rest.replace("^", ".")
        pieces = [part for part in rest.split(".") if part]

        def _to_int(value: str):
            try:
                digits = "".join(ch for ch in value if ch.isdigit())
                return int(digits) if digits else None
            except Exception:
                return None

        if len(pieces) >= 1:
            field = _to_int(pieces[0])
        if len(pieces) >= 2:
            component = _to_int(pieces[1])
        if len(pieces) >= 3:
            subcomponent = _to_int(pieces[2])
    return (segment or None), field, component, subcomponent


def _extract_issue_value(message: Any) -> str | None:
    if not message:
        return None
    text = str(message)
    for pattern in _ISSUE_VALUE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        for group in match.groups():
            if group:
                return group
    return None


def _enrich_validate_issues(issues: Any) -> list[dict[str, Any]]:
    """Ensure validation issues expose code, segment, field, component, subcomponent."""
    enriched: list[dict[str, Any]] = []
    for issue in issues or []:
        if isinstance(issue, dict):
            item = dict(issue)
        else:
            item = {"message": str(issue)}
        seg = item.get("segment")
        field = item.get("field")
        component = item.get("component")
        subcomponent = item.get("subcomponent")
        location = item.get("location")
        parsed = _parse_hl7_location(location)
        seg = seg or parsed[0]
        if field in ("", None):
            field = parsed[1]
        if component in ("", None):
            component = parsed[2]
        if subcomponent in ("", None):
            subcomponent = parsed[3]
        severity = (item.get("severity") or "error").lower()
        if "warn" in severity:
            severity = "warning"
        elif "err" in severity or "fail" in severity:
            severity = "error"
        elif any(tag in severity for tag in ("info", "ok", "pass")):
            severity = "info"
        else:
            severity = severity or "error"
        message_text = item.get("message") or ""
        enriched.append(
            {
                "severity": severity,
                "code": item.get("code")
                or item.get("rule")
                or item.get("id")
                or item.get("type")
                or "",
                "segment": seg or "",
                "field": field,
                "component": component,
                "subcomponent": subcomponent,
                "location": location or "",
                "occurrence": item.get("occurrence"),
                "message": message_text,
                "value": item.get("value") or _extract_issue_value(message_text),
            }
        )
    return enriched


def _hl7_value_for_position(
    message: str,
    segment: str | None,
    field: int | None,
    component: int | None = None,
    subcomponent: int | None = None,
) -> str | None:
    """Return the first value for the given HL7 segment/field position."""
    if not message or not segment or field is None:
        return None
    seg = segment.strip().upper()
    if not seg or field <= 0:
        return None
    for line in (message or "").splitlines():
        if not line.startswith(seg + "|"):
            continue
        parts = line.split("|")
        if len(parts) <= field:
            continue
        value = parts[field] or ""
        if component and component > 0:
            comp_parts = value.split("^")
            if len(comp_parts) >= component:
                value = comp_parts[component - 1] or ""
            else:
                value = ""
        if subcomponent and subcomponent > 0:
            sub_parts = value.split("&")
            if len(sub_parts) >= subcomponent:
                value = sub_parts[subcomponent - 1] or ""
            else:
                value = ""
        return value or None
    return None


def _build_success_rows(
    template: dict[str, Any] | None,
    issues: list[dict[str, Any]],
    message_text: str,
) -> list[dict[str, Any]]:
    """Create synthetic OK rows for checks that passed."""
    if not template:
        return []
    checks = (template or {}).get("checks") or []
    if not isinstance(checks, list):
        return []
    failed_fields: set[tuple[str | None, int | None]] = set()
    failed_components: set[tuple[str | None, int | None, int | None, int | None]] = set()
    for issue in issues:
        sev = (issue.get("severity") or "").lower()
        if sev in {"error", "warning"}:
            seg_key = (issue.get("segment") or "").strip().upper() or None
            failed_fields.add((seg_key, issue.get("field")))
            failed_components.add(
                (
                    seg_key,
                    issue.get("field"),
                    issue.get("component"),
                    issue.get("subcomponent"),
                )
            )

    success_rows: list[dict[str, Any]] = []
    for raw in checks:
        if not isinstance(raw, dict):
            continue
        segment = (raw.get("segment") or "").strip().upper()
        field_val = raw.get("field")
        try:
            field_int = int(field_val)
        except Exception:
            continue
        seg_key = (segment or "").strip().upper() or None
        comp_val = raw.get("component")
        sub_val = raw.get("subcomponent")
        try:
            comp_int = int(comp_val) if comp_val not in (None, "") else None
        except Exception:
            comp_int = None
        try:
            sub_int = int(sub_val) if sub_val not in (None, "") else None
        except Exception:
            sub_int = None
        if (seg_key, field_int) in failed_fields:
            continue
        if (seg_key, field_int, comp_int, sub_int) in failed_components:
            continue
        value = _hl7_value_for_position(message_text, segment or None, field_int, comp_int, sub_int)
        success_rows.append(
            {
                "severity": "ok",
                "code": "OK",
                "segment": segment or "",
                "field": field_int,
                "component": comp_int,
                "subcomponent": sub_int,
                "occurrence": None,
                "location": f"{segment}-{field_int}" if segment else "",
                "message": "",
                "value": value,
            }
        )
    return success_rows


def _count_issue_severities(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"ok": 0, "warnings": 0, "errors": 0}
    for row in rows:
        sev = (row.get("severity") or "").lower()
        if sev == "ok":
            counts["ok"] += 1
        elif sev == "warning":
            counts["warnings"] += 1
        elif sev == "error":
            counts["errors"] += 1
    return counts


async def parse_any_request(request: Request) -> dict:
    """Parse JSON, multipart, urlencoded, or query data into a dict."""
    ctype = (request.headers.get("content-type") or "").lower()
    try:
        query = dict(request.query_params)
    except KeyError:
        query = {}
    raw = await request.body()
    query_string = request.scope.get("query_string", b"")
    if isinstance(query_string, bytes):
        query_text = query_string.decode("latin-1", errors="ignore")
    else:
        query_text = str(query_string)
    _debug_log(
        "parse_any_request.start",
        method=request.method,
        path=request.url.path,
        query=query_text,
        ctype=ctype,
        content_length=request.headers.get("content-length"),
        hx=request.headers.get("hx-request"),
        raw_preview=_preview(raw),
    )

    body: dict[str, Any] = {}

    if raw and ("application/json" in ctype or "text/json" in ctype):
        try:
            parsed = json.loads(raw.decode("utf-8"))
            if isinstance(parsed, dict):
                body = dict(parsed)
        except Exception:
            body = {}

    if not body and "multipart/form-data" in ctype:
        try:
            form = await request.form()
            data: dict[str, Any] = {}
            for key, value in form.multi_items():
                if isinstance(value, UploadFile):
                    data.setdefault(key, value.filename)
                else:
                    data.setdefault(key, value)
            for key, value in query.items():
                data.setdefault(key, value)
            body = {k: _coerce_scalar(v) for k, v in data.items()}
        except Exception:
            body = {}

    if not body and "application/x-www-form-urlencoded" in ctype:
        try:
            form = await request.form()
            body = {key: form.get(key) for key in form.keys()} if form else {}
        except Exception:
            body = {}

    if not body and raw:
        try:
            parsed = parse_qs(raw.decode("utf-8", errors="replace"), keep_blank_values=True)
            body = {k: _coerce_scalar(v) for k, v in parsed.items()}
        except Exception:
            body = {}

    for key, value in query.items():
        body.setdefault(key, value)

    if "count" in body:
        try:
            body["count"] = int(body["count"])
        except Exception:
            pass

    if not body.get("trigger"):
        rel = str(body.get("template_relpath") or "").strip()
        if rel:
            stem = Path(rel).stem
            if stem:
                body["trigger"] = stem

    try:
        cnt_value = body.get("count", 1)
        if isinstance(cnt_value, str):
            cnt = int(cnt_value) if cnt_value.strip() else 1
        else:
            cnt = int(cnt_value)
    except Exception:
        cnt = 1
    deid_value = body.get("deidentify")
    missing_deidentify = "deidentify" not in body
    if not missing_deidentify:
        if deid_value is None:
            missing_deidentify = True
        elif isinstance(deid_value, str):
            missing_deidentify = deid_value.strip() == ""
    if cnt > 1 and missing_deidentify:
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
    start_ts = time.time()
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
    deid_template_name = body.get("deid_template")
    deid_template = _maybe_load_deid_template(deid_template_name)
    apply_baseline = _to_bool(body.get("apply_baseline"))
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
            if deid_template or apply_baseline:
                tpl_payload = deid_template or {"rules": []}
                msg = apply_deid_with_template(msg, tpl_payload, apply_baseline=apply_baseline)
            else:
                msg = deidentify_message(msg, seed=derived)
        msgs.append(msg)
    first_preview = msgs[0] if msgs else ""
    _debug_log(
        "generate_messages.done",
        messages=len(msgs),
        rel=rel or "inline",
        deidentify=deidentify,
        deid_template=deid_template_name or "",
        baseline=apply_baseline,
        ensure_unique=ensure_unique,
        include_clinical=include_clinical,
        preview=first_preview,
    )
    out = "\n".join(msgs) + ("\n" if msgs else "")
    _debug_log("generate_messages.response_ready", bytes=len(out))
    template_name = Path(rel).name if rel else "inline"
    log_activity(
        "generate",
        version=version,
        trigger=trig or "",
        count=count,
        template=template_name,
    )
    msg_id = str(uuid.uuid4())
    elapsed_ms = int((time.time() - start_ts) * 1000)
    try:
        record_event(
            {
                "stage": "generate",
                "msg_id": msg_id,
                "hl7_type": trig or "",
                "hl7_version": version,
                "status": "success",
                "elapsed_ms": elapsed_ms,
                "count": len(msgs),
                "template": template_name,
                "size_bytes": len(out.encode("utf-8", errors="ignore")),
            }
        )
    except Exception:
        logger.debug("metrics.record_event_failed", exc_info=True)
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
    _debug_log(
        "generate_messages_plain.invoke",
        method=request.method,
        path=request.url.path,
        query=request.url.query,
        hx=request.headers.get("hx-request"),
        accept=request.headers.get("accept"),
        referer=request.headers.get("referer"),
    )
    body = await parse_any_request(request)
    _debug_log("generate_messages_plain.parsed_body", body=body)
    return generate_messages(body)


async def try_generate_on_validation_error(
    request: Request, exc: RequestValidationError
):
    """Attempt to salvage legacy validation failures for /api/interop/generate."""
    path = request.url.path.rstrip("/")
    if path not in {"/api/interop/generate", "/api/interop/generate/plain"}:
        _debug_log("validation_fallback.skip_path", path=path)
        return None
    errors = exc.errors() if hasattr(exc, "errors") else []
    _debug_log("validation_fallback.recovering", path=path, errors=errors)
    try:
        body = await parse_any_request(request)
        _debug_log("validation_fallback.recovered_body", path=path, body=body)
        return generate_messages(body)
    except Exception:
        logger.exception("Failed to recover generator request after validation error")
        _debug_log("validation_fallback.failed", path=path)
        return None

def _wants_text_plain(request: Request) -> bool:
    """Return True when client prefers text/plain (or ?format=txt)."""
    accept = (request.headers.get("accept") or "").lower()
    if "text/plain" in accept:
        return True
    qs = (request.url.query or "").lower()
    return ("format=txt" in qs) or ("format=text" in qs) or ("format=plain" in qs)


def _wants_validation_html(request: Request, format_hint: Any | None = None) -> bool:
    """Detect when the caller expects an HTML validation report."""

    def _is_html(value: Any) -> bool:
        try:
            return str(value).strip().lower() == "html"
        except Exception:
            return False

    if _is_html(format_hint):
        return True

    try:
        query_format = request.query_params.get("format")  # type: ignore[attr-defined]
    except Exception:
        query_format = None
    if _is_html(query_format):
        return True

    headers = request.headers
    hx_header = headers.get("hx-request") or headers.get("HX-Request")
    if hx_header is not None:
        try:
            if str(hx_header).strip().lower() == "true":
                return True
        except Exception:
            return True
    accept = (headers.get("accept") or headers.get("Accept") or "").lower()
    return "text/html" in accept


def _normalize_validation_result(raw: Any, message_text: str) -> dict[str, Any]:
    """Map validator output into counts + issue rows for the UI report."""

    def _as_list(value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            return list(value)
        return [value]

    if not isinstance(raw, dict):
        raw = {"ok": bool(raw), "raw": raw}

    issues: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()
    ok_count = 1 if raw.get("ok") else 0
    warn_count = 0
    err_count = 0

    def append_issue(severity: str, code: str | None, location: str | None, message: str | None) -> None:
        nonlocal warn_count, err_count
        sev_raw = str(severity or "info").lower()
        if "warn" in sev_raw:
            normalized = "warning"
        elif any(tag in sev_raw for tag in ("err", "fail")):
            normalized = "error"
        elif "info" in sev_raw or "ok" in sev_raw or "pass" in sev_raw:
            normalized = "info"
        else:
            normalized = "info"
        code_text = (code or "").strip() or "—"
        raw_location = (location or "").strip()
        location_text = raw_location or "—"
        message_text_local = (message or "").strip()
        key = (normalized, code_text, location_text, message_text_local)
        if key in seen:
            return
        seen.add(key)
        if normalized == "error":
            err_count += 1
        elif normalized == "warning":
            warn_count += 1
        issues.append(
            {
                "severity": normalized,
                "code": code_text,
                "location": raw_location,
                "message": message_text_local or "—",
            }
        )

    # Structured issues (already include severity/code/location/message)
    for entry in _as_list(raw.get("issues")):
        if isinstance(entry, dict):
            append_issue(
                entry.get("severity") or entry.get("level") or entry.get("status") or "info",
                entry.get("code") or entry.get("rule") or entry.get("id") or entry.get("type"),
                entry.get("location")
                or entry.get("segment")
                or entry.get("field")
                or entry.get("path")
                or entry.get("target"),
                entry.get("message") or entry.get("detail") or entry.get("description") or str(entry),
            )
        else:
            append_issue("info", None, None, str(entry))

    # Errors may be returned as list[str], list[dict], or dict[str, Any]
    errors = raw.get("errors")
    if isinstance(errors, dict):
        for key, value in errors.items():
            append_issue("error", str(key), None, value if isinstance(value, str) else str(value))
    else:
        for idx, entry in enumerate(_as_list(errors), start=1):
            if isinstance(entry, dict):
                append_issue(
                    entry.get("severity") or "error",
                    entry.get("code") or entry.get("rule") or f"E{idx:03}",
                    entry.get("location")
                    or entry.get("segment")
                    or entry.get("field")
                    or entry.get("path"),
                    entry.get("message") or entry.get("detail") or str(entry),
                )
            else:
                append_issue("error", f"E{idx:03}", None, str(entry))

    # Warnings mirror the error shapes
    warnings = raw.get("warnings") or raw.get("warning")
    for idx, entry in enumerate(_as_list(warnings), start=1):
        if isinstance(entry, dict):
            append_issue(
                entry.get("severity") or entry.get("level") or "warning",
                entry.get("code") or entry.get("rule") or f"W{idx:03}",
                entry.get("location")
                or entry.get("segment")
                or entry.get("field")
                or entry.get("path"),
                entry.get("message") or entry.get("detail") or str(entry),
            )
        else:
            append_issue("warning", f"W{idx:03}", None, str(entry))

    counts_payload = raw.get("counts")
    if isinstance(counts_payload, dict):
        try:
            ok_count = max(ok_count, int(counts_payload.get("ok") or counts_payload.get("pass") or 0))
        except Exception:
            pass
        try:
            warn_count = max(warn_count, int(counts_payload.get("warnings") or counts_payload.get("warning") or 0))
        except Exception:
            pass
        try:
            err_count = max(err_count, int(counts_payload.get("errors") or counts_payload.get("error") or 0))
        except Exception:
            pass

    if err_count == 0 and warn_count == 0:
        ok_count = max(ok_count, 1 if (message_text or raw.get("validated_message")) else ok_count)

    normalized_message = raw.get("validated_message") or raw.get("message") or message_text or ""

    return {
        "counts": {"ok": ok_count, "warnings": warn_count, "errors": err_count},
        "issues": issues,
        "validated_message": str(normalized_message or ""),
        "raw": raw,
    }


def _field_label(seg: str, idx: int) -> str:
    NAMES = {
        "PID": {
            3: "Patient Identifier List",
            5: "Patient Name",
            7: "Date/Time of Birth",
            8: "Administrative Sex",
            11: "Patient Address",
            13: "Phone Number - Home",
            18: "Patient Account Number",
        },
        "PV1": {
            2: "Patient Class",
            3: "Assigned Patient Location",
            7: "Attending Doctor",
            19: "Visit Number",
        },
        "NK1": {2: "Name", 3: "Relationship", 4: "Address", 5: "Phone"},
        "DG1": {3: "Diagnosis Code", 6: "Diagnosis Type"},
        "AL1": {3: "Allergen", 4: "Allergen Type"},
        "IN1": {3: "Insurance Plan", 4: "Insurance Company", 36: "Policy Number"},
    }
    title = NAMES.get(seg, {}).get(idx, "")
    return f"{seg}-{idx}" + (f" ({title})" if title else "")


def _summarize_hl7_changes(orig: str, deid: str) -> list[dict[str, Any]]:
    """Very small, segment/field delta summary for common segments."""

    def _lines(s: str) -> list[str]:
        return [ln for ln in re.split(r"\r?\n", s or "") if ln.strip()]

    a, b = _lines(orig), _lines(deid)
    n = min(len(a), len(b))
    out: list[dict[str, Any]] = []
    for i in range(n):
        fa = a[i].split("|")
        fb = b[i].split("|")
        seg = (fa[0] if fa else "UNK")[:3]
        m = max(len(fa), len(fb))
        for idx in range(1, m):
            va = fa[idx] if idx < len(fa) else ""
            vb = fb[idx] if idx < len(fb) else ""
            if va != vb:
                out.append(
                    {
                        "segment": seg,
                        "field": idx,
                        "label": _field_label(seg, idx),
                        "before": va,
                        "after": vb,
                    }
                )
    return out


def _render_deid_summary_html(changes: list[dict[str, Any]]) -> str:
    template = templates.get_template("ui/interop/_deid_summary.html")
    return template.render({"changes": changes})


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
    text_value = text if isinstance(text, str) else str(text)
    template = _maybe_load_deid_template(body.get("deid_template") or body.get("template"))
    apply_baseline = _to_bool(body.get("apply_baseline"))
    if template or apply_baseline:
        tpl_payload = template or {"rules": []}
        out = apply_deid_with_template(text_value, tpl_payload, apply_baseline=apply_baseline)
    else:
        out = deidentify_message(text_value, seed=seed_int)
    changes = _summarize_hl7_changes(text_value, out)
    log_activity(
        "deidentify",
        length=len(text_value),
        mode=body.get("mode") or "",
        changed=len(changes),
        template=body.get("deid_template") or "",
        baseline=apply_baseline,
    )
    if _wants_text_plain(request):
        return PlainTextResponse(
            out, media_type="text/plain", headers={"Cache-Control": "no-store"}
        )
    json_changes = [
        {
            "field": c.get("label") or f"{c.get('segment','')}-{c.get('field','')}",
            "before": c.get("before", ""),
            "after": c.get("after", ""),
        }
        for c in changes
    ]
    return JSONResponse({"text": out, "changes": json_changes})


@router.post("/api/interop/deidentify/summary")
async def api_deidentify_summary(request: Request):
    """Return a compact HTML (or JSON) report of fields changed by de-identification."""
    body = await parse_any_request(request)
    text = body.get("text") or ""
    seed = body.get("seed")
    try:
        seed_int = int(seed) if seed not in (None, "") else None
    except Exception:
        seed_int = None
    src = text if isinstance(text, str) else str(text)
    template = _maybe_load_deid_template(body.get("deid_template") or body.get("template"))
    apply_baseline = _to_bool(body.get("apply_baseline"))
    if template or apply_baseline:
        tpl_payload = template or {"rules": []}
        deid = apply_deid_with_template(src, tpl_payload, apply_baseline=apply_baseline)
    else:
        deid = deidentify_message(src, seed=seed_int)
    changes = _summarize_hl7_changes(src, deid)
    accept = (request.headers.get("accept") or "").lower()
    if "text/html" in accept:
        return HTMLResponse(_render_deid_summary_html(changes))
    return JSONResponse({"count": len(changes), "changes": changes})


@router.post("/api/interop/validate")
async def api_validate(request: Request):
    """Validate HL7; accept JSON, form, multipart, or query."""
    body = await parse_any_request(request)
    text_value = body.get("message")
    if text_value is None:
        text_value = body.get("text") or ""
    text = text_value if isinstance(text_value, str) else str(text_value or "")
    profile = body.get("profile")
    template = _maybe_load_validation_template(body.get("val_template") or body.get("template"))
    if template:
        results = validate_with_template(text, template)
    else:
        results = validate_message(text, profile=profile)
    log_activity(
        "validate",
        version=body.get("version") or "",
        workbook=bool(body.get("workbook")),
        profile=profile or "",
        template=body.get("val_template") or "",
    )
    format_hint = body.get("format")
    model = _normalize_validation_result(results, text)
    enriched = _enrich_validate_issues(model.get("issues"))
    success_rows = _build_success_rows(template, enriched, text)
    combined_rows = enriched + success_rows
    model["issues"] = combined_rows
    model["counts"] = _count_issue_severities(combined_rows)
    if _wants_validation_html(request, format_hint=format_hint):
        return templates.TemplateResponse(
            "ui/interop/_validate_report.html",
            {"request": request, "r": model},
        )
    return JSONResponse(model)


@router.post("/api/interop/mllp/send")
async def api_mllp_send(request: Request):
    """Send messages over MLLP; accept JSON, form, multipart, or query."""
    body = await parse_any_request(request)
    host = (body.get("host") or "").strip()
    port = int(body.get("port") or 0)
    timeout = float(body.get("timeout") or 5.0)
    messages = (
        body.get("messages")
        or body.get("message")
        or body.get("text")
        or ""
    )
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
    log_activity(
        "mllp_send",
        host=host,
        port=port,
        messages=len(messages_list),
        timeout=timeout,
    )
    return JSONResponse({"sent": len(messages_list), "acks": acks})
