from __future__ import annotations

from fastapi import APIRouter, Request
from starlette.templating import Jinja2Templates

from api.ui import install_link_for

router = APIRouter()
templates = Jinja2Templates(directory="templates")
install_link_for(templates)


@router.get("/ui/agents", name="ui_agents_home")
async def agents_home(request: Request):
    """Render the primary Agent landing page."""

    return templates.TemplateResponse("ui/agents/index.html", {"request": request})


@router.post("/ui/agents/demo")
async def agents_demo(request: Request):
    """Stub endpoint for initiating the scripted agent demo workflow."""

    return templates.TemplateResponse("ui/agents/demo_started.html", {"request": request})
