from __future__ import annotations

import json
from datetime import datetime, timezone
import os
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from starlette.templating import Jinja2Templates
from api.ui import install_link_for
from api.interop_gen import generate_messages, parse_any_request, _normalize_validation_result
from silhouette_core.interop.deid import deidentify_message, apply_deid_with_template
from silhouette_core.interop.validate_workbook import validate_message, validate_with_template
from api.debug_log import (
    LOG_FILE,
    tail_debug_lines,
    is_debug_enabled,
    log_debug_event,
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")
install_link_for(templates)

DEID_DIR = Path("configs/interop/deid_templates")
VAL_DIR = Path("configs/interop/validate_templates")


def _ensure_dirs() -> None:
    DEID_DIR.mkdir(parents=True, exist_ok=True)
    VAL_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Legacy Manual Pipeline presets & helpers
# ---------------------------------------------------------------------------
PIPELINE_PRESETS: dict[str, dict[str, object]] = {
    "local-2575": {
        "label": "Local MLLP (127.0.0.1:2575)",
        "host": "127.0.0.1",
        "port": 2575,
        "timeout": 5,
        "fhir_endpoint": "http://127.0.0.1:8080/fhir",
        "post_fhir": False,
    },
    "docker-2575": {
        "label": "Docker MLLP (localhost:2575)",
        "host": "localhost",
        "port": 2575,
        "timeout": 5,
        "fhir_endpoint": "http://localhost:8080/fhir",
        "post_fhir": False,
    },
}


def _pipeline_defaults(preset_key: str | None) -> dict[str, object]:
    preset = PIPELINE_PRESETS.get((preset_key or "").strip()) or {}
    return {
        "host": preset.get("host", ""),
        "port": preset.get("port", ""),
        "timeout": preset.get("timeout", 5),
        "fhir_endpoint": preset.get("fhir_endpoint", ""),
        "post_fhir": bool(preset.get("post_fhir", False)),
    }


def list_deid_templates() -> list[str]:
    _ensure_dirs()
    return [p.stem for p in sorted(DEID_DIR.glob("*.json"))]


def list_validation_templates() -> list[str]:
    _ensure_dirs()
    return [p.stem for p in sorted(VAL_DIR.glob("*.json"))]


def load_deid_template(name: str) -> dict:
    _ensure_dirs()
    path = DEID_DIR / f"{name}.json"
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"De-identify template '{name}' not found")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - malformed template
        raise HTTPException(status_code=400, detail=f"Invalid template JSON: {exc}") from exc


def load_validation_template(name: str) -> dict:
    _ensure_dirs()
    path = VAL_DIR / f"{name}.json"
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"Validation template '{name}' not found")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - malformed template
        raise HTTPException(status_code=400, detail=f"Invalid template JSON: {exc}") from exc

def _template_lists() -> tuple[list[str], list[str]]:
    return list_deid_templates(), list_validation_templates()


def _maybe_load_deid_template(name: str | None) -> dict | None:
    if not name:
        return None
    normalized = str(name).strip()
    if not normalized or normalized.lower() in {"builtin", "legacy", "none"}:
        return None
    return load_deid_template(normalized)


def _maybe_load_validation_template(name: str | None) -> dict | None:
    if not name:
        return None
    normalized = str(name).strip()
    if not normalized or normalized.lower() in {"builtin", "legacy", "none"}:
        return None
    return load_validation_template(normalized)


def _safe_url_for(request: Request, name: str, fallback: str) -> str:
    try:
        return str(request.url_for(name))
    except Exception:
        return fallback

def _ui_urls(request: Request) -> dict[str, str]:
    """
    Provide all URLs the templates need, with hardcoded fallbacks so the UI
    keeps working even if a route name changes.
    """
    return {
        # UI form posts (HTML fallback):
        "ui_generate":   _safe_url_for(request, "ui_generate",   "/ui/interop/generate"),
        "ui_deidentify": _safe_url_for(request, "ui_deidentify", "/ui/interop/deidentify"),
        "ui_validate":   _safe_url_for(request, "ui_validate",   "/ui/interop/validate"),
        "ui_pipeline":   _safe_url_for(request, "ui_interop_pipeline", "/ui/interop/pipeline"),
        # API endpoints (HTMX fast path):
        "api_generate":  _safe_url_for(request, "generate_messages_endpoint", "/api/interop/generate"),
        "api_deidentify": _safe_url_for(request, "api_deidentify", "/api/interop/deidentify"),
        "api_deidentify_summary": _safe_url_for(
            request,
            "api_deidentify_summary",
            "/api/interop/deidentify/summary",
        ),
        "api_validate": _safe_url_for(request, "api_validate", "/api/interop/validate"),
        "api_validate_view": _safe_url_for(request, "interop_validate_view", "/api/interop/validate/view"),
        "api_pipeline_run": _safe_url_for(request, "run_pipeline", "/api/interop/pipeline/run"),
    }

@router.get("/ui/interop/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    deid, val = _template_lists()
    return templates.TemplateResponse(
        "ui/interop/skills.html",
        {"request": request, "urls": _ui_urls(request), "deid_templates": deid, "val_templates": val},
    )


@router.get("/ui/interop/skills", response_class=HTMLResponse)
async def interop_skills(request: Request):
    deid, val = _template_lists()
    return templates.TemplateResponse(
        "ui/interop/skills.html",
        {"request": request, "urls": _ui_urls(request), "deid_templates": deid, "val_templates": val},
    )


@router.get("/ui/interop/pipeline", response_class=HTMLResponse, name="ui_interop_pipeline")
async def interop_pipeline(request: Request, preset: str | None = None, skin: str | None = None):
    """
    Dispatcher for Manual Pipeline:
    - Legacy skin (default): SIL_INTEROP_LEGACY=1 or ?skin=legacy
    - V2 skin: ?skin=v2 or SIL_INTEROP_LEGACY=0
    """

    prefer_legacy = os.getenv("SIL_INTEROP_LEGACY", "1") == "1"
    use_legacy = (skin or "").lower() != "v2" if prefer_legacy else (skin or "").lower() == "legacy"
    if use_legacy:
        from api.ui_legacy_pipeline import ui_legacy_pipeline

        return await ui_legacy_pipeline(request, preset=preset)

    deid_templates, val_templates = _template_lists()
    defaults = _pipeline_defaults(preset)
    ctx = {
        "request": request,
        "deid_templates": deid_templates,
        "val_templates": val_templates,
        "urls": _ui_urls(request),
        "presets": PIPELINE_PRESETS,
        "preset_key": preset or "",
        "defaults": defaults,
        "log_path": str(LOG_FILE),
        "limit": 200,
        "refreshed": "",
        "rows": [],
    }
    return templates.TemplateResponse("ui/interop/pipeline.html", ctx)


@router.get("/ui/interop/history", response_class=HTMLResponse)
async def history(request: Request):
    root = Path("out/interop")
    files = sorted(root.glob("*/active/*.json"), reverse=True)
    items = [p.as_posix() for p in files]
    return templates.TemplateResponse("interop/history.html", {"request": request, "items": items, "urls": _ui_urls(request)})

@router.get("/ui/interop/logs/content", response_class=HTMLResponse)
async def interop_logs_content(request: Request, limit: int = 200):
    lines = tail_debug_lines(limit)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    ctx = {
        "request": request,
        "lines": lines,
        "limit": limit,
        "log_path": str(LOG_FILE),
        "enabled": is_debug_enabled(),
        "refreshed": ts,
    }
    return templates.TemplateResponse("ui/interop/_debug_log_content.html", ctx)


@router.get("/ui/interop/history/view")
async def history_view(path: str):
    base = Path("out").resolve()
    p = Path(path)
    try:
        target = p.resolve()
    except FileNotFoundError:
        raise HTTPException(404)
    if not target.is_file() or not str(target).startswith(str(base)):
        raise HTTPException(404)
    return PlainTextResponse(target.read_text(encoding="utf-8"), media_type="application/json")


# Pure-HTML fallback: when JS is disabled, the form posts here and we render a page.
@router.post("/ui/interop/generate", response_class=HTMLResponse)
async def ui_generate(request: Request):
    log_debug_event(
        "ui.generate.invoke",
        method=request.method,
        path=request.url.path,
        query=request.url.query,
        hx=request.headers.get("hx-request"),
        accept=request.headers.get("accept"),
        referer=request.headers.get("referer"),
        content_type=request.headers.get("content-type"),
    )
    body = await parse_any_request(request)
    log_debug_event(
        "ui.generate.body",
        keys=";".join(sorted(body.keys())),
        trigger=body.get("trigger"),
        template=body.get("template_relpath"),
        count=body.get("count"),
    )
    try:
        resp = generate_messages(body)
    except HTTPException as exc:
        log_debug_event(
            "ui.generate.error",
            status=exc.status_code,
            detail=getattr(exc, "detail", ""),
        )
        raise
    text = resp.body.decode("utf-8") if hasattr(resp, "body") else str(resp)
    accept = (request.headers.get("accept") or "").lower()
    hx = (request.headers.get("hx-request") or "").lower() == "true"
    log_debug_event(
        "ui.generate.result",
        hx=hx,
        accept=accept,
        bytes=len(text.encode("utf-8", errors="ignore")),
    )
    if hx or "text/plain" in accept:
        return PlainTextResponse(text, media_type="text/plain")
    return templates.TemplateResponse(
        "ui/interop/generate_result.html",
        {"request": request, "hl7_text": text}
    )

# De-identify (HTML fragment suitable for hx-swap)
@router.post("/ui/interop/deidentify", response_class=HTMLResponse)
async def ui_deidentify(request: Request):
    body = await parse_any_request(request)
    text = (body.get("text") or "").strip()
    seed = body.get("seed")
    try:
        seed_int = int(seed) if seed not in (None, "") else None
    except Exception:
        seed_int = None
    if not text:
        return HTMLResponse("<div class='muted'>No input.</div>")
    raw_baseline = body.get("apply_baseline")
    baseline_flag = False
    if raw_baseline not in (None, ""):
        baseline_flag = str(raw_baseline).strip().lower() in {"1", "true", "on", "yes"}
    tpl = _maybe_load_deid_template(body.get("deid_template") or body.get("template"))
    if tpl or baseline_flag:
        tpl_payload = tpl or {"rules": []}
        out = apply_deid_with_template(text, tpl_payload, apply_baseline=baseline_flag)
    else:
        out = deidentify_message(text, seed=seed_int)
    return HTMLResponse(f"<pre class='codepane'>{out}</pre>")

# Validate (HTML fragment suitable for hx-swap)
@router.post("/ui/interop/validate", response_class=HTMLResponse)
async def ui_validate(request: Request):
    body = await parse_any_request(request)
    text = body.get("message") or body.get("text") or ""
    profile = body.get("profile")
    tpl = _maybe_load_validation_template(body.get("val_template") or body.get("template"))
    if tpl:
        res = validate_with_template(text, tpl)
    else:
        res = validate_message(text, profile=profile)
    normalized = _normalize_validation_result(res, text)
    errors = [it for it in normalized.get("issues", []) if it.get("severity") == "error"]
    warnings = [it for it in normalized.get("issues", []) if it.get("severity") == "warning"]
    ok_badge = "<span class='chip'>OK</span>" if res.get("ok") else "<span class='chip'>Issues</span>"
    err_html = "".join(
        f"<li><code>{(it.get('location') or it.get('segment') or '—')}</code> — {it.get('message') or ''}</li>"
        for it in errors
    )
    warn_html = "".join(
        f"<li class='muted'><code>{(it.get('location') or it.get('segment') or '—')}</code> — {it.get('message') or ''}</li>"
        for it in warnings
    )
    html = (
        "<div class='mt'><strong>Analyze</strong> "
        + ok_badge
        + "<div class='grid2'>"
        + f"<div><em>Errors</em><ul>{err_html or '<li>None</li>'}</ul></div>"
        + f"<div><em>Warnings</em><ul class='muted'>{warn_html or '<li>None</li>'}</ul></div>"
        + "</div></div>"
    )
    return HTMLResponse(html)

