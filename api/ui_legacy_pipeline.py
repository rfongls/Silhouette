from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from starlette.templating import Jinja2Templates

from api.ui import install_link_for

router = APIRouter()
templates = Jinja2Templates(directory="templates")
install_link_for(templates)

# Legacy template stores (for dropdowns)
DEID_DIR = Path("configs/interop/deid_templates")
VAL_DIR = Path("configs/interop/validate_templates")
for p in (DEID_DIR, VAL_DIR):
    p.mkdir(parents=True, exist_ok=True)


def _list_templates(d: Path) -> list[str]:
    return [p.stem for p in sorted(d.glob("*.json"))]


def _safe_url_for(request: Request, name: str, fallback: str) -> str:
    try:
        return str(request.url_for(name))
    except Exception:  # pragma: no cover - defensive fallback
        return fallback


def _legacy_urls(request: Request) -> dict[str, str]:
    return {
        "ui_generate": _safe_url_for(request, "ui_generate", "/ui/interop/generate"),
        "ui_deidentify": _safe_url_for(request, "ui_deidentify", "/ui/interop/deidentify"),
        "ui_validate": _safe_url_for(request, "ui_validate", "/ui/interop/validate"),
        "api_generate": _safe_url_for(
            request, "generate_messages_endpoint", "/api/interop/generate"
        ),
        "api_deidentify": _safe_url_for(request, "api_deidentify", "/api/interop/deidentify"),
        "api_validate": _safe_url_for(request, "api_validate", "/api/interop/validate"),
        "api_validate_view": _safe_url_for(
            request, "interop_validate_view", "/api/interop/validate/view"
        ),
        "api_pipeline_run": _safe_url_for(request, "run_pipeline", "/api/interop/pipeline/run"),
        "mllp_send": _safe_url_for(request, "api_mllp_send", "/api/interop/mllp/send"),
        "ui_pipeline": _safe_url_for(request, "ui_interop_pipeline", "/ui/interop/pipeline"),
        "logs_content": _safe_url_for(request, "interop_logs_content", "/ui/interop/logs/content"),
    }


# Presets used by legacy bench
PIPELINE_PRESETS = {
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


def _defaults(preset: str | None) -> dict:
    p = PIPELINE_PRESETS.get((preset or "").strip()) or {}
    return {
        "host": p.get("host", ""),
        "port": p.get("port", ""),
        "timeout": p.get("timeout", 5),
        "fhir_endpoint": p.get("fhir_endpoint", ""),
        "post_fhir": bool(p.get("post_fhir", False)),
    }


@router.get(
    "/ui/interop/pipeline/legacy",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def ui_legacy_pipeline(request: Request, preset: str | None = None):
    """Legacy QA bench (pre-V2 look/flow) with V2-safe context."""

    ctx = {
        "request": request,
        "legacy_urls": _legacy_urls(request),
        "presets": PIPELINE_PRESETS,
        "preset_key": preset or "",
        "defaults": _defaults(preset),
        "deid_templates": _list_templates(DEID_DIR),
        "val_templates": _list_templates(VAL_DIR),
        "log_path": "out/interop/server_http.log",
        "limit": 200,
        "refreshed": "",
    }
    return templates.TemplateResponse("ui/interop/legacy/pipeline.html", ctx)
