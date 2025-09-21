"""Explicit /ui/home route that renders the existing dashboard template."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from api.ui import install_link_for

router = APIRouter()
_templates = Jinja2Templates(directory=str(Path("templates")))
install_link_for(_templates)


@router.get("/ui/home", response_class=HTMLResponse)
async def ui_home(request: Request) -> HTMLResponse:
    """Render the Home dashboard and ensure the FastAPI request is provided."""
    return _templates.TemplateResponse("ui/home_reports.html", {"request": request})
