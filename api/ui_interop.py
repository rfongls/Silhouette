from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from starlette.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/ui/interop/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    tmpl_dir = Path("templates/hl7")
    triggers = []
    if tmpl_dir.exists():
        for p in tmpl_dir.glob("*.hl7.j2"):
            name = p.stem
            if "_" in name:
                triggers.append(name)
    triggers = sorted(set(triggers)) or ["ADT_A01", "ORU_R01", "VXU_V04"]
    return templates.TemplateResponse("ui/interop/dashboard.html", {"request": request, "triggers": triggers})


@router.get("/ui/interop/history", response_class=HTMLResponse)
async def history(request: Request):
    root = Path("out/interop")
    files = sorted(root.glob("*/active/*.json"), reverse=True)
    items = [p.as_posix() for p in files]
    return templates.TemplateResponse("interop/history.html", {"request": request, "items": items})


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

