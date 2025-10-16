"""Legacy 10/06-style standalone Interop pipeline (isolated shell).

Enable via env ``SILH_STANDALONE_ENABLE=1``. Routes mount under
``/ui/standalone/*`` and are completely optional for deployments that only
need the modern pipeline UI.
"""
from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.templating import Jinja2Templates

from api.ui import install_link_for

from api.ui_interop import (
    PIPELINE_PRESETS,
    LOG_FILE,
    _pipeline_defaults,
    _ui_urls,
    list_deid_templates,
    list_validation_templates,
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")
install_link_for(templates)


def _is_truthy(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"", "0", "false", "off"}


def _standalone_enabled() -> bool:
    return _is_truthy(os.getenv("SILH_STANDALONE_ENABLE", "1"), default=True)


def _safe_url_for(request: Request, name: str, fallback: str) -> str:
    try:
        return str(request.url_for(name))
    except Exception:
        return fallback


def _legacy_urls(request: Request) -> dict[str, str]:
    urls: dict[str, str] = dict(_ui_urls(request))
    urls.update(
        {
            "ui_deid_templates": _safe_url_for(
                request, "deid_template_options", "/ui/standalone/deid/templates"
            ),
            "ui_val_templates": _safe_url_for(
                request, "validate_template_options", "/ui/standalone/validate/templates"
            ),
            "mllp_send": _safe_url_for(request, "api_mllp_send", "/api/interop/mllp/send"),
            "logs_content": _safe_url_for(
                request, "interop_logs_content", "/ui/interop/logs/content"
            ),
            "samples": _safe_url_for(request, "list_hl7_samples", "/api/interop/samples"),
            "sample": _safe_url_for(request, "get_hl7_sample", "/api/interop/sample"),
            "triggers": _safe_url_for(request, "triggers_json", "/api/interop/triggers"),
        }
    )
    return urls


def _template_context(request: Request, preset: str | None) -> dict[str, Any]:
    deid_templates = list_deid_templates()
    val_templates = list_validation_templates()
    defaults = _pipeline_defaults(preset)
    return {
        "request": request,
        "urls": _legacy_urls(request),
        "deid_templates": deid_templates,
        "val_templates": val_templates,
        "presets": PIPELINE_PRESETS,
        "preset_key": preset or "",
        "defaults": defaults,
        "log_path": str(LOG_FILE),
        "limit": 200,
        "refreshed": "",
        "rows": [],
    }


@router.get("/ui/standalone/pipeline", response_class=HTMLResponse)
async def standalone_pipeline(request: Request, preset: str | None = None) -> HTMLResponse:
    if not _standalone_enabled():
        return HTMLResponse("Standalone UI is disabled (set SILH_STANDALONE_ENABLE=1).", status_code=404)
    ctx = _template_context(request, preset)
    return templates.TemplateResponse("standalone_1006/pipeline.html", ctx)


@router.get("/ui/standalonepipeline", include_in_schema=False)
async def standalone_redirect(request: Request) -> RedirectResponse:
    if not _standalone_enabled():
        return RedirectResponse(url="/", status_code=302)
    target = _safe_url_for(request, "standalone_pipeline", "/ui/standalone/pipeline")
    return RedirectResponse(url=target, status_code=307)


@router.get("/ui/standalone/deid/templates", response_class=HTMLResponse)
async def deid_template_options(request: Request) -> HTMLResponse:
    if not _standalone_enabled():
        return HTMLResponse("", status_code=404)
    options = ["<option value=\"\">— choose a rule —</option>"]
    options.extend(f'<option value="{name}">{name}</option>' for name in list_deid_templates())
    return HTMLResponse("\n".join(options))


@router.get("/ui/standalone/validate/templates", response_class=HTMLResponse)
async def validate_template_options(request: Request) -> HTMLResponse:
    if not _standalone_enabled():
        return HTMLResponse("", status_code=404)
    options = ["<option value=\"\">— choose a rule —</option>"]
    options.extend(f'<option value="{name}">{name}</option>' for name in list_validation_templates())
    return HTMLResponse("\n".join(options))


def install(app) -> None:
    if _standalone_enabled():
        app.include_router(router)
