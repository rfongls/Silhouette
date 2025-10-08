"""Feature-flagged Engine UI routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from api.ui import install_link_for, templates as base_templates

router = APIRouter()

templates = base_templates
install_link_for(templates)


@router.get("/ui/engine", response_class=HTMLResponse, name="ui_engine_index")
def ui_engine_index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("ui/engine/index.html", {"request": request})
