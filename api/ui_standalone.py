from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from starlette.templating import Jinja2Templates

from api.ui import install_link_for

router = APIRouter()
templates = Jinja2Templates(directory="templates")
install_link_for(templates)

_DEID_DIR = Path("configs/interop/deid_templates")
_VAL_DIR = Path("configs/interop/validate_templates")
for directory in (_DEID_DIR, _VAL_DIR):
    directory.mkdir(parents=True, exist_ok=True)


def _list_templates(directory: Path) -> list[str]:
    return [path.stem for path in sorted(directory.glob("*.json"))]


def _safe_url_for(request: Request, name: str, fallback: str) -> str:
    try:
        return str(request.url_for(name))
    except Exception:
        return fallback


def _urls(request: Request) -> dict[str, str]:
    return {
        "ui_pipeline": _safe_url_for(request, "ui_interop_pipeline", "/ui/interop/pipeline"),
        "api_generate": _safe_url_for(request, "generate_messages_endpoint", "/api/interop/generate"),
        "api_deidentify": _safe_url_for(request, "api_deidentify", "/api/interop/deidentify"),
        "api_deidentify_summary": _safe_url_for(
            request, "api_deidentify_summary", "/api/interop/deidentify/summary"
        ),
        "api_validate": _safe_url_for(request, "api_validate", "/api/interop/validate"),
        "api_validate_view": _safe_url_for(
            request, "interop_validate_view", "/api/interop/validate/view"
        ),
        "ui_deidentify": _safe_url_for(request, "ui_deidentify", "/ui/interop/deidentify"),
        "ui_validate": _safe_url_for(request, "ui_validate", "/ui/interop/validate"),
        "ui_deid_templates": _safe_url_for(
            request, "ui_deid_templates", "/ui/standalone/deid/templates"
        ),
        "ui_val_templates": _safe_url_for(
            request, "ui_val_templates", "/ui/standalone/validate/templates"
        ),
        "api_pipeline_run": _safe_url_for(request, "run_pipeline", "/api/interop/pipeline/run"),
        "mllp_send": _safe_url_for(request, "api_mllp_send", "/api/interop/mllp/send"),
        "logs_content": _safe_url_for(request, "interop_logs_content", "/ui/interop/logs/content"),
        "triggers": _safe_url_for(request, "triggers_json", "/api/interop/triggers"),
        "samples": _safe_url_for(request, "list_hl7_samples", "/api/interop/samples"),
        "sample": _safe_url_for(request, "get_hl7_sample", "/api/interop/sample"),
    }


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


def _defaults(preset: str | None) -> dict[str, object]:
    info = PIPELINE_PRESETS.get((preset or "").strip()) or {}
    return {
        "host": info.get("host", ""),
        "port": info.get("port", ""),
        "timeout": info.get("timeout", 5),
        "fhir_endpoint": info.get("fhir_endpoint", ""),
        "post_fhir": bool(info.get("post_fhir", False)),
    }


@router.get("/ui/standalone/pipeline", response_class=HTMLResponse, name="ui_standalone_pipeline")
def ui_standalone_pipeline(request: Request, preset: str | None = None) -> HTMLResponse:
    ctx = {
        "request": request,
        "urls": _urls(request),
        "presets": PIPELINE_PRESETS,
        "preset_key": preset or "",
        "defaults": _defaults(preset),
        "deid_templates": _list_templates(_DEID_DIR),
        "val_templates": _list_templates(_VAL_DIR),
    }
    return templates.TemplateResponse("standalone_1006/pipeline.html", ctx)


@router.get("/ui/standalonepipeline", include_in_schema=False, name="_compat_standalone_pipeline")
def _compat_standalone_pipeline() -> RedirectResponse:
    return RedirectResponse(url="/ui/standalone/pipeline", status_code=307)


@router.get("/ui/standalone/deid/templates", name="ui_deid_templates")
def ui_deid_templates() -> Response:
    options = ["<option value=\"\">— choose a rule —</option>"]
    options.extend(f'<option value="{name}">{name}</option>' for name in _list_templates(_DEID_DIR))
    return Response("\n".join(options), media_type="text/html")


@router.get("/ui/standalone/validate/templates", name="ui_val_templates")
def ui_val_templates() -> Response:
    options = ["<option value=\"\">— choose a rule —</option>"]
    options.extend(f'<option value="{name}">{name}</option>' for name in _list_templates(_VAL_DIR))
    return Response("\n".join(options), media_type="text/html")
