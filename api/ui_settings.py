from __future__ import annotations

import json
from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from starlette.templating import Jinja2Templates

from api.ui import install_link_for
from silhouette_core.interop.template_store import (
    list_deid_templates,
    list_validation_templates,
    load_deid_template,
    load_validation_template,
    save_deid_template,
    save_validation_template,
    delete_deid_template,
    delete_validation_template,
    export_deid_csv,
    export_validation_csv,
    import_deid_csv,
    import_validation_csv,
)


router = APIRouter()
templates = Jinja2Templates(directory="templates")
install_link_for(templates)


def _deid_rows(form) -> list[dict[str, object]]:
    segments = form.getlist("rules-segment")
    fields = form.getlist("rules-field")
    components = form.getlist("rules-component")
    subcomponents = form.getlist("rules-subcomponent")
    actions = form.getlist("rules-action")
    params = form.getlist("rules-param")
    max_len = max(len(segments), len(fields), len(components), len(subcomponents), len(actions), len(params))
    rules: list[dict[str, object]] = []
    for idx in range(max_len):
        segment = (segments[idx] if idx < len(segments) else "").strip().upper()
        field = (fields[idx] if idx < len(fields) else "").strip()
        if not segment or not field:
            continue
        rule = {
            "segment": segment,
            "field": field,
            "component": (components[idx] if idx < len(components) else "").strip(),
            "subcomponent": (subcomponents[idx] if idx < len(subcomponents) else "").strip(),
            "action": (actions[idx] if idx < len(actions) else "redact").strip().lower() or "redact",
            "param": (params[idx] if idx < len(params) else "").strip(),
        }
        rules.append(rule)
    return rules


def _validation_rows(form) -> list[dict[str, object]]:
    segments = form.getlist("checks-segment")
    fields = form.getlist("checks-field")
    patterns = form.getlist("checks-pattern")
    allowed = form.getlist("checks-allowed")
    required_indices = {str(v) for v in form.getlist("checks-required")}
    max_len = max(len(segments), len(fields), len(patterns), len(allowed))
    checks: list[dict[str, object]] = []
    for idx in range(max_len):
        segment = (segments[idx] if idx < len(segments) else "").strip().upper()
        field = (fields[idx] if idx < len(fields) else "").strip()
        if not segment or not field:
            continue
        pattern = (patterns[idx] if idx < len(patterns) else "").strip()
        allowed_raw = (allowed[idx] if idx < len(allowed) else "").strip()
        checks.append(
            {
                "segment": segment,
                "field": field,
                "required": str(idx) in required_indices,
                "pattern": pattern,
                "allowed_values": allowed_raw,
            }
        )
    return checks


def _template_summaries() -> dict[str, list[dict[str, object]]]:
    deid_items: list[dict[str, object]] = []
    for name in list_deid_templates():
        try:
            tpl = load_deid_template(name)
            count = len(tpl.get("rules") or [])
        except Exception:
            count = 0
        deid_items.append({"name": name, "count": count})

    val_items: list[dict[str, object]] = []
    for name in list_validation_templates():
        try:
            tpl = load_validation_template(name)
            count = len(tpl.get("checks") or [])
        except Exception:
            count = 0
        val_items.append({"name": name, "count": count})

    return {"deid": deid_items, "validation": val_items}


@router.get("/ui/settings", response_class=HTMLResponse, name="ui_settings_index")
async def settings_index(request: Request):
    summaries = _template_summaries()
    ctx = {
        "request": request,
        "deid_templates": summaries["deid"],
        "val_templates": summaries["validation"],
    }
    return templates.TemplateResponse("ui/settings/index.html", ctx)


def _deid_edit_context(request: Request, template: dict[str, object], *, is_new: bool) -> dict[str, object]:
    return {
        "request": request,
        "template": template,
        "is_new": is_new,
    }


def _val_edit_context(request: Request, template: dict[str, object], *, is_new: bool) -> dict[str, object]:
    return {
        "request": request,
        "template": template,
        "is_new": is_new,
    }


@router.get("/ui/settings/deid/new", response_class=HTMLResponse, name="ui_settings_deid_new")
async def deid_new(request: Request):
    tpl = {"name": "", "version": "v1", "rules": []}
    return templates.TemplateResponse("ui/settings/deid_edit.html", _deid_edit_context(request, tpl, is_new=True))


@router.get("/ui/settings/deid/{name}", response_class=HTMLResponse, name="ui_settings_deid_edit")
async def deid_edit(request: Request, name: str):
    try:
        tpl = load_deid_template(name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Template not found")
    return templates.TemplateResponse("ui/settings/deid_edit.html", _deid_edit_context(request, tpl, is_new=False))


@router.post("/ui/settings/deid/save", name="ui_settings_deid_save")
async def deid_save(
    request: Request,
    original_name: str = Form(""),
    name: str = Form(...),
    version: str = Form("v1"),
):
    form = await request.form()
    data = {
        "name": name,
        "version": version or "v1",
        "rules": _deid_rows(form),
    }
    saved = save_deid_template(data, original_name=original_name or None)
    url = request.url_for("ui_settings_deid_edit", name=saved["name"])
    return RedirectResponse(url=url, status_code=303)


@router.post("/ui/settings/deid/delete", name="ui_settings_deid_delete")
async def deid_delete(request: Request, name: str = Form(...)):
    delete_deid_template(name)
    url = request.url_for("ui_settings_index")
    return RedirectResponse(url=url, status_code=303)


@router.post("/ui/settings/deid/import", name="ui_settings_deid_import")
async def deid_import(request: Request, name: str = Form(...), file: UploadFile = File(...)):
    content = (await file.read()).decode("utf-8", errors="ignore")
    import_deid_csv(name, content)
    url = request.url_for("ui_settings_deid_edit", name=name)
    return RedirectResponse(url=url, status_code=303)


@router.get("/ui/settings/deid/{name}/export.json", name="ui_settings_deid_export_json")
async def deid_export_json(name: str):
    tpl = load_deid_template(name)
    payload = json.dumps(tpl, indent=2)
    headers = {"Content-Disposition": f"attachment; filename={name}.json"}
    return Response(content=payload, media_type="application/json", headers=headers)


@router.get("/ui/settings/deid/{name}/export.csv", name="ui_settings_deid_export_csv")
async def deid_export_csv(name: str):
    tpl = load_deid_template(name)
    csv_text = export_deid_csv(tpl)
    headers = {"Content-Disposition": f"attachment; filename={name}.csv"}
    return Response(content=csv_text, media_type="text/csv", headers=headers)


@router.get("/ui/settings/validation/new", response_class=HTMLResponse, name="ui_settings_val_new")
async def val_new(request: Request):
    tpl = {"name": "", "version": "v1", "checks": []}
    return templates.TemplateResponse("ui/settings/val_edit.html", _val_edit_context(request, tpl, is_new=True))


@router.get("/ui/settings/validation/{name}", response_class=HTMLResponse, name="ui_settings_val_edit")
async def val_edit(request: Request, name: str):
    try:
        tpl = load_validation_template(name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Template not found")
    return templates.TemplateResponse("ui/settings/val_edit.html", _val_edit_context(request, tpl, is_new=False))


@router.post("/ui/settings/validation/save", name="ui_settings_val_save")
async def val_save(
    request: Request,
    original_name: str = Form(""),
    name: str = Form(...),
    version: str = Form("v1"),
):
    form = await request.form()
    data = {
        "name": name,
        "version": version or "v1",
        "checks": _validation_rows(form),
    }
    saved = save_validation_template(data, original_name=original_name or None)
    url = request.url_for("ui_settings_val_edit", name=saved["name"])
    return RedirectResponse(url=url, status_code=303)


@router.post("/ui/settings/validation/delete", name="ui_settings_val_delete")
async def val_delete(request: Request, name: str = Form(...)):
    delete_validation_template(name)
    url = request.url_for("ui_settings_index")
    return RedirectResponse(url=url, status_code=303)


@router.post("/ui/settings/validation/import", name="ui_settings_val_import")
async def val_import(request: Request, name: str = Form(...), file: UploadFile = File(...)):
    content = (await file.read()).decode("utf-8", errors="ignore")
    import_validation_csv(name, content)
    url = request.url_for("ui_settings_val_edit", name=name)
    return RedirectResponse(url=url, status_code=303)


@router.get("/ui/settings/validation/{name}/export.json", name="ui_settings_val_export_json")
async def val_export_json(name: str):
    tpl = load_validation_template(name)
    payload = json.dumps(tpl, indent=2)
    headers = {"Content-Disposition": f"attachment; filename={name}.json"}
    return Response(content=payload, media_type="application/json", headers=headers)


@router.get("/ui/settings/validation/{name}/export.csv", name="ui_settings_val_export_csv")
async def val_export_csv(name: str):
    tpl = load_validation_template(name)
    csv_text = export_validation_csv(tpl)
    headers = {"Content-Disposition": f"attachment; filename={name}.csv"}
    return Response(content=csv_text, media_type="text/csv", headers=headers)
