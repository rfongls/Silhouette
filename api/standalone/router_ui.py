from __future__ import annotations
import os
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from starlette.templating import Jinja2Templates
from .template_resolver import find_template

router = APIRouter()
templates = Jinja2Templates(directory="templates")
# Expose resolver to Jinja ONLY for standalone pages
templates.env.globals["find_template"] = find_template

DEID_DIR = Path("configs/standalone/deid_templates")
VAL_DIR  = Path("configs/standalone/validate_templates")
for p in (DEID_DIR, VAL_DIR):
    p.mkdir(parents=True, exist_ok=True)
    if not list(p.glob("*.json")):
        # Bootstrap defaults if directory is empty
        if "deid" in str(p):
            (p / "default.json").write_text('{"name":"default","rules":[]}', encoding="utf-8")
        else:
            (p / "default.json").write_text('{"name":"default","checks":[]}', encoding="utf-8")

def _list_templates(dirpath: Path) -> list[str]:
    return [p.stem for p in sorted(dirpath.glob("*.json"))]


PIPELINE_SUGGESTIONS: dict[str, list[dict[str, str]]] = {
    "gen": [
        {
            "action": "deid",
            "label": "De-identify",
            "description": "Apply configured de-identification rules",
        },
        {
            "action": "validate",
            "label": "Validate",
            "description": "Check the generated message structure",
        },
    ],
    "deid": [
        {
            "action": "validate",
            "label": "Validate",
            "description": "Review structure after de-identification",
        },
        {
            "action": "pipeline",
            "label": "HL7 → FHIR",
            "description": "Open pipeline builder in a new tab",
            "requires": "pipeline",
        },
    ],
    "validate": [
        {
            "action": "mllp",
            "label": "Send via MLLP",
            "description": "Deliver message and view ACK",
            "requires": "mllp",
        },
        {
            "action": "pipeline",
            "label": "HL7 → FHIR",
            "description": "Translate the validated message",
            "requires": "pipeline",
        },
    ],
    "mllp": [
        {
            "action": "pipeline",
            "label": "HL7 → FHIR",
            "description": "Translate and validate via pipeline",
            "requires": "pipeline",
        }
    ],
}


def _safe_url_for(request: Request, name: str, fallback: str) -> str:
    try:
        return str(request.url_for(name))
    except Exception:  # pragma: no cover - defensive fallback
        return fallback


def _standalone_urls(request: Request) -> Dict[str, str]:
    root = request.scope.get("root_path", "") or ""
    return {
        "ui_generate": _safe_url_for(request, "ui_generate", f"{root}/ui/interop/generate"),
        "api_generate": _safe_url_for(
            request, "generate_messages_endpoint", f"{root}/api/interop/generate"
        ),
        "ui_deidentify": _safe_url_for(request, "ui_deidentify", f"{root}/ui/interop/deidentify"),
        "api_deidentify": _safe_url_for(request, "api_deidentify", f"{root}/api/interop/deidentify"),
        "api_deidentify_summary": _safe_url_for(
            request, "api_deidentify_summary", f"{root}/api/interop/deidentify/summary"
        ),
        "ui_validate": _safe_url_for(request, "ui_validate", f"{root}/ui/interop/validate"),
        "api_validate": _safe_url_for(request, "api_validate", f"{root}/api/interop/validate"),
        "api_validate_view": _safe_url_for(
            request, "interop_validate_view", f"{root}/api/interop/validate/view"
        ),
        "api_pipeline_run": _safe_url_for(request, "run_pipeline", f"{root}/api/interop/pipeline/run"),
        "ui_pipeline": _safe_url_for(request, "ui_interop_pipeline", f"{root}/ui/interop/pipeline"),
        "mllp_send": _safe_url_for(request, "api_mllp_send", f"{root}/api/interop/mllp/send"),
        "logs_content": _safe_url_for(
            request, "interop_logs_content", f"{root}/ui/interop/logs/content"
        ),
        "samples": _safe_url_for(request, "list_hl7_samples", f"{root}/api/interop/samples"),
        "sample": _safe_url_for(request, "get_hl7_sample", f"{root}/api/interop/sample"),
        "triggers": _safe_url_for(request, "triggers_json", f"{root}/api/interop/triggers"),
        "ui_deid_templates": _safe_url_for(
            request, "standalone_deid_templates", f"{root}/standalone/deid/templates"
        ),
        "ui_val_templates": _safe_url_for(
            request, "standalone_val_templates", f"{root}/standalone/validate/templates"
        ),
        "module_action": _safe_url_for(
            request, "standalone_module_action", f"{root}/standalone/api/module/action"
        ),
    }


def _mllp_defaults() -> Dict[str, object]:
    return {
        "host": os.getenv("STANDALONE_MLLP_HOST", "127.0.0.1"),
        "port": int(os.getenv("STANDALONE_MLLP_PORT", "2575") or 2575),
        "timeout": int(os.getenv("STANDALONE_MLLP_TIMEOUT", "5") or 5),
    }

@router.get("/", name="standalone_index")
def index(request: Request) -> HTMLResponse:
    """
    Standalone landing page. If templates/standalone/index.html exists, we use it.
    Otherwise, we render a compact index_compat.html which includes panels by resolver.
    """
    legacy_dir = Path("templates/standalone/legacy")
    legacy_dir.mkdir(parents=True, exist_ok=True)
    for fname, minimal in {
        "_generate_panel.html": "<section id='generate-panel' class='panel'><pre id='gen-output' class='mono'></pre></section>",
        "_deid_panel.html": "<section id='deid-panel' class='panel collapsed'><pre id='deid-output' class='mono'></pre></section>",
        "_validate_panel.html": "<section id='validate-panel' class='panel collapsed'><div id='validate-output' class='report'></div></section>",
        "_mllp_panel.html": "<section id='mllp-panel' class='panel collapsed'><div id='mllp-output'></div></section>",
        "_action_tray.html": "<div class='action-tray' hidden></div>",
    }.items():
        target = legacy_dir / fname
        if not target.exists():
            target.write_text(minimal, encoding="utf-8")

    page = find_template("index.html") or "standalone/index_compat.html"

    ctx = {
        "request": request,
        "urls": _standalone_urls(request),
        "deid_templates": _list_templates(DEID_DIR),
        "val_templates": _list_templates(VAL_DIR),
        "defaults": _mllp_defaults(),
        "pipeline_recs": PIPELINE_SUGGESTIONS,
    }
    return templates.TemplateResponse(page, ctx)


@router.get("/deid/templates", name="standalone_deid_templates", response_class=HTMLResponse)
def deid_template_options() -> HTMLResponse:
    options = ["<option value=\"\">— choose a rule —</option>"]
    options.extend(f'<option value="{name}">{name}</option>' for name in _list_templates(DEID_DIR))
    return HTMLResponse("\n".join(options))


@router.get("/validate/templates", name="standalone_val_templates", response_class=HTMLResponse)
def validate_template_options() -> HTMLResponse:
    options = ["<option value=\"\">— choose a rule —</option>"]
    options.extend(f'<option value="{name}">{name}</option>' for name in _list_templates(VAL_DIR))
    return HTMLResponse("\n".join(options))
