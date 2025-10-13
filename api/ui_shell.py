"""Shell landing and skill hub pages."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from api.ui import templates as ui_templates


router = APIRouter(tags=["ui-shell"])


@router.get("/ui", response_class=HTMLResponse, name="ui_shell_home")
async def ui_home(request: Request) -> HTMLResponse:
    return ui_templates.TemplateResponse(
        "ui/shell/landing.html",
        {"request": request},
    )


@router.get("/ui/skills", response_class=HTMLResponse, name="ui_skills_index")
async def ui_skills(request: Request) -> HTMLResponse:
    return ui_templates.TemplateResponse(
        "ui/skills/index.html",
        {"request": request},
    )


@router.get("/ui/skills/interop", response_class=HTMLResponse, name="ui_skills_interop")
async def ui_skills_interop(request: Request) -> HTMLResponse:
    return ui_templates.TemplateResponse(
        "ui/skills/interop/index.html",
        {"request": request},
    )


@router.get(
    "/ui/skills/interop/settings",
    response_class=HTMLResponse,
    name="ui_skills_interop_settings",
)
async def ui_skills_interop_settings(request: Request) -> HTMLResponse:
    transform_profile_id = request.query_params.get("transform_profile_id")
    return ui_templates.TemplateResponse(
        "ui/skills/interop/settings.html",
        {"request": request, "transform_profile_id": transform_profile_id},
    )


@router.get("/ui/skills/cyber", response_class=HTMLResponse, name="ui_skills_cyber")
async def ui_skills_cyber(request: Request) -> HTMLResponse:
    return ui_templates.TemplateResponse(
        "ui/skills/cyber/index.html",
        {"request": request},
    )


@router.get("/ui/chat", response_class=HTMLResponse, name="ui_shell_chat")
async def ui_chat(request: Request) -> HTMLResponse:
    return ui_templates.TemplateResponse(
        "ui/shell/chat.html",
        {"request": request},
    )
