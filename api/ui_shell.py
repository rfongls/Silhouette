"""Shell landing, skill hubs, and Interop settings utilities."""
from __future__ import annotations

import json

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.exc import IntegrityError

from api.ui import templates as ui_templates
from insights.store import get_store


router = APIRouter(tags=["ui-shell"])


def _serialize_profile(profile) -> dict:
    return {
        "id": profile.id,
        "kind": profile.kind,
        "name": profile.name,
        "description": profile.description or "",
        "config": profile.config or {},
        "config_json": json.dumps(profile.config or {}),
    }


def _render_profile_partial(request: Request, kind: str) -> HTMLResponse:
    store = get_store()
    items = [_serialize_profile(p) for p in store.list_profiles(kind)]
    template = f"ui/skills/interop/partials/{kind}_list.html"
    return ui_templates.TemplateResponse(template, {"request": request, "items": items})


def _clean_name(raw: str) -> str:
    name = (raw or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    return name


def _clean_description(raw: str | None) -> str | None:
    description = (raw or "").strip()
    return description or None


@router.get("/", include_in_schema=False)
async def redirect_root() -> RedirectResponse:
    return RedirectResponse(url="/ui/home", status_code=307)


@router.get("/ui", include_in_schema=False, name="ui_shell_home")
async def ui_home_redirect() -> RedirectResponse:
    return RedirectResponse(url="/ui/home", status_code=307)


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
    store = get_store()
    transform_items = [_serialize_profile(p) for p in store.list_profiles("transform")]
    deid_items = [_serialize_profile(p) for p in store.list_profiles("deid")]
    validate_items = [_serialize_profile(p) for p in store.list_profiles("validate")]
    return ui_templates.TemplateResponse(
        "ui/skills/interop/settings.html",
        {
            "request": request,
            "transform_profile_id": transform_profile_id,
            "transform_items": transform_items,
            "deid_items": deid_items,
            "validate_items": validate_items,
        },
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


def _parse_profile_id(raw_id: str) -> int:
    try:
        return int(raw_id)
    except (TypeError, ValueError):  # pragma: no cover - defensive guard
        raise HTTPException(status_code=400, detail="invalid profile_id")


@router.post(
    "/ui/skills/interop/settings/transform/create",
    response_class=HTMLResponse,
    name="ui_skills_interop_transform_create",
)
async def interop_transform_create(
    request: Request,
    name: str = Form(...),
    description: str | None = Form(None),
) -> HTMLResponse:
    store = get_store()
    try:
        store.create_profile(
            kind="transform",
            name=_clean_name(name),
            description=_clean_description(description),
            config={"rules": []},
        )
    except IntegrityError as exc:  # pragma: no cover - depends on DB engine
        raise HTTPException(status_code=409, detail="profile name already exists") from exc
    return _render_profile_partial(request, "transform")


@router.post(
    "/ui/skills/interop/settings/transform/update",
    response_class=HTMLResponse,
    name="ui_skills_interop_transform_update",
)
async def interop_transform_update(
    request: Request,
    profile_id: str = Form(...),
    name: str = Form(...),
    description: str | None = Form(None),
) -> HTMLResponse:
    store = get_store()
    if not store.update_profile(
        _parse_profile_id(profile_id),
        name=_clean_name(name),
        description=_clean_description(description),
    ):
        raise HTTPException(status_code=404, detail="profile not found")
    return _render_profile_partial(request, "transform")


@router.post(
    "/ui/skills/interop/settings/transform/delete",
    response_class=HTMLResponse,
    name="ui_skills_interop_transform_delete",
)
async def interop_transform_delete(
    request: Request,
    profile_id: str = Form(...),
) -> HTMLResponse:
    store = get_store()
    try:
        ok = store.delete_profile(_parse_profile_id(profile_id))
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not ok:
        raise HTTPException(status_code=404, detail="profile not found")
    return _render_profile_partial(request, "transform")


@router.get(
    "/ui/skills/interop/settings/transform/list",
    response_class=HTMLResponse,
    name="ui_skills_interop_transform_list",
)
async def interop_transform_list(request: Request) -> HTMLResponse:
    return _render_profile_partial(request, "transform")


@router.post(
    "/ui/skills/interop/settings/deid/create",
    response_class=HTMLResponse,
    name="ui_skills_interop_deid_create",
)
async def interop_deid_create(
    request: Request,
    name: str = Form(...),
    description: str | None = Form(None),
) -> HTMLResponse:
    store = get_store()
    try:
        store.create_profile(
            kind="deid",
            name=_clean_name(name),
            description=_clean_description(description),
            config={},
        )
    except IntegrityError as exc:  # pragma: no cover
        raise HTTPException(status_code=409, detail="profile name already exists") from exc
    return _render_profile_partial(request, "deid")


@router.post(
    "/ui/skills/interop/settings/deid/update",
    response_class=HTMLResponse,
    name="ui_skills_interop_deid_update",
)
async def interop_deid_update(
    request: Request,
    profile_id: str = Form(...),
    name: str = Form(...),
    description: str | None = Form(None),
) -> HTMLResponse:
    store = get_store()
    if not store.update_profile(
        _parse_profile_id(profile_id),
        name=_clean_name(name),
        description=_clean_description(description),
    ):
        raise HTTPException(status_code=404, detail="profile not found")
    return _render_profile_partial(request, "deid")


@router.post(
    "/ui/skills/interop/settings/deid/delete",
    response_class=HTMLResponse,
    name="ui_skills_interop_deid_delete",
)
async def interop_deid_delete(
    request: Request,
    profile_id: str = Form(...),
) -> HTMLResponse:
    store = get_store()
    try:
        ok = store.delete_profile(_parse_profile_id(profile_id))
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not ok:
        raise HTTPException(status_code=404, detail="profile not found")
    return _render_profile_partial(request, "deid")


@router.get(
    "/ui/skills/interop/settings/deid/list",
    response_class=HTMLResponse,
    name="ui_skills_interop_deid_list",
)
async def interop_deid_list(request: Request) -> HTMLResponse:
    return _render_profile_partial(request, "deid")


@router.post(
    "/ui/skills/interop/settings/validate/create",
    response_class=HTMLResponse,
    name="ui_skills_interop_validate_create",
)
async def interop_validate_create(
    request: Request,
    name: str = Form(...),
    description: str | None = Form(None),
) -> HTMLResponse:
    store = get_store()
    try:
        store.create_profile(
            kind="validate",
            name=_clean_name(name),
            description=_clean_description(description),
            config={},
        )
    except IntegrityError as exc:  # pragma: no cover
        raise HTTPException(status_code=409, detail="profile name already exists") from exc
    return _render_profile_partial(request, "validate")


@router.post(
    "/ui/skills/interop/settings/validate/update",
    response_class=HTMLResponse,
    name="ui_skills_interop_validate_update",
)
async def interop_validate_update(
    request: Request,
    profile_id: str = Form(...),
    name: str = Form(...),
    description: str | None = Form(None),
) -> HTMLResponse:
    store = get_store()
    if not store.update_profile(
        _parse_profile_id(profile_id),
        name=_clean_name(name),
        description=_clean_description(description),
    ):
        raise HTTPException(status_code=404, detail="profile not found")
    return _render_profile_partial(request, "validate")


@router.get(
    "/ui/skills/interop/settings/validate/list",
    response_class=HTMLResponse,
    name="ui_skills_interop_validate_list",
)
async def interop_validate_list(request: Request) -> HTMLResponse:
    return _render_profile_partial(request, "validate")


@router.post(
    "/ui/skills/interop/settings/validate/delete",
    response_class=HTMLResponse,
    name="ui_skills_interop_validate_delete",
)
async def interop_validate_delete(
    request: Request,
    profile_id: str = Form(...),
) -> HTMLResponse:
    store = get_store()
    try:
        ok = store.delete_profile(_parse_profile_id(profile_id))
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not ok:
        raise HTTPException(status_code=404, detail="profile not found")
    return _render_profile_partial(request, "validate")
