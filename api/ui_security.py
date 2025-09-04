from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from starlette.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/ui/security/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("security/dashboard.html", {"request": request})


@router.get("/ui/security/history", response_class=HTMLResponse)
async def history(request: Request):
    root = Path("out/security")
    files = sorted(root.glob("*/active/*.json"), reverse=True)
    items = [str(p) for p in files]
    return templates.TemplateResponse("security/history.html", {"request": request, "items": items})


@router.get("/ui/security/history/view")
async def history_view(path: str):
    p = Path(path)
    if not p.exists():
        raise HTTPException(404)
    return PlainTextResponse(p.read_text(encoding="utf-8"), media_type="application/json")
