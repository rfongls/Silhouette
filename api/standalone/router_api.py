from __future__ import annotations
import json
from pathlib import Path
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import PlainTextResponse, HTMLResponse
from starlette.templating import Jinja2Templates
from .adapters import do_generate, do_deidentify, do_validate
from .template_resolver import find_template, resolve_include

router = APIRouter()
templates = Jinja2Templates(directory="templates")

DEID_DIR = Path("configs/standalone/deid_templates")
VAL_DIR  = Path("configs/standalone/validate_templates")

def _load_template(dirpath: Path, name: str) -> dict:
    p = dirpath / f"{name}.json"
    if not p.exists():
        raise HTTPException(400, f"Template '{name}' not found")
    return json.loads(p.read_text(encoding="utf-8"))

@router.post("/generate", name="standalone_generate")
def generate(
    message: str = Form(""),
    trigger: str = Form("VXU^V04"),
) -> PlainTextResponse:
    """
    Legacy-compatible generate; returns text/plain HL7 output.
    """
    out = do_generate({"message": message, "trigger": trigger})
    return PlainTextResponse(out)

@router.post("/deidentify", name="standalone_deidentify")
def deidentify(
    message: str = Form(...),
    template_name: str = Form("default"),
    format: str = Form("txt"),
):
    """
    De-identify. Returns text/plain by default; can return a simple HTML <pre> if format=html.
    """
    tpl = _load_template(DEID_DIR, template_name)
    text, summary = do_deidentify(message, tpl)
    if format == "html":
        return HTMLResponse(f"<div class='deid-result'><h4>De-identification</h4><pre>{text}</pre></div>")
    return PlainTextResponse(text)

@router.post("/validate", name="standalone_validate")
def validate(
    message: str = Form(...),
    template_name: str = Form("default"),
    format: str = Form("html"),
):
    """
    Validate. Returns HTML fragment by default (matches legacy panel behavior).
    """
    tpl = _load_template(VAL_DIR, template_name)
    result = do_validate(message, tpl)
    if format == "html":
        # Try to use a template if present, else fall back to a simple <pre>
        tmpl = find_template("_validate_report.html")
        if tmpl:
            include_path, _ = resolve_include("_validate_report.html")
            return templates.TemplateResponse(include_path, {
                "request": None,
                "result": result,
            })
        return HTMLResponse(f"<div class='val-report'><h4>Validation Result</h4><pre>{json.dumps(result, indent=2)}</pre></div>")
    return PlainTextResponse(json.dumps(result))


@router.post("/module/action", name="standalone_module_action", response_class=HTMLResponse)
def module_action(
    module: str = Form("interop.pipeline"),
    function: str = Form("run"),
    action: str = Form(""),
    params: str = Form(""),
    payload: str = Form(""),
    message: str = Form(""),
) -> HTMLResponse:
    text = (payload or message or "").strip()
    summary = {
        "module": (module or "interop").strip() or "interop",
        "function": (function or action or "run").strip() or "run",
        "params": params or "",
        "chars": len(text),
        "empty": not text,
    }
    return templates.TemplateResponse(
        "standalone/legacy/_module_action_result.html",
        {"request": None, "summary": summary},
    )
