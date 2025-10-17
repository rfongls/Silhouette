from __future__ import annotations
import json
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from starlette.templating import Jinja2Templates
from .template_resolver import find_template, resolve_include

router = APIRouter()
templates = Jinja2Templates(directory="templates")
# Expose resolver to Jinja ONLY for standalone pages
templates.env.globals["find_template"] = find_template
templates.env.globals["resolve_include"] = resolve_include

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

@router.get("/", name="standalone_index")
def index(request: Request) -> HTMLResponse:
    """
    Standalone landing page. If templates/standalone/index.html exists, we use it.
    Otherwise, we render a compact index_compat.html which includes panels by resolver.
    """
    page = find_template("index.html") or "standalone/index_compat.html"
    ctx = {
        "request": request,
        "deid_templates": _list_templates(DEID_DIR),
        "val_templates": _list_templates(VAL_DIR),
    }
    return templates.TemplateResponse(page, ctx)
