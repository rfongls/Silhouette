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
    legacy_dir = Path("templates/standalone/legacy")
    legacy_dir.mkdir(parents=True, exist_ok=True)
    for fname, minimal in {
        "_generate_panel.html": "<section id='generate-panel' class='panel'><pre id='gen-output' class='mono'></pre></section>",
        "_deid_panel.html": "<section id='deid-panel' class='panel collapsed'><pre id='deid-output' class='mono'></pre></section>",
        "_validate_panel.html": "<section id='validate-panel' class='panel collapsed'><div id='validate-output' class='report'></div></section>",
    }.items():
        target = legacy_dir / fname
        if not target.exists():
            target.write_text(minimal, encoding="utf-8")

    page = find_template("index.html") or "standalone/index_compat.html"

    gen_include, gen_src = resolve_include("_generate_panel.html")
    deid_include, deid_src = resolve_include("_deid_panel.html")
    val_include, val_src = resolve_include("_validate_panel.html")

    ctx = {
        "request": request,
        "deid_templates": _list_templates(DEID_DIR),
        "val_templates": _list_templates(VAL_DIR),
        "gen_include": gen_include,
        "deid_include": deid_include,
        "val_include": val_include,
        "debug_standalone_includes": {
            "generate": gen_src,
            "deid": deid_src,
            "validate": val_src,
        },
    }
    return templates.TemplateResponse(page, ctx)
