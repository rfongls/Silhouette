from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")
router = APIRouter(tags=["ui"])


@router.get("/reports", name="ui_reports")
def reports(request: Request):
    return templates.TemplateResponse("reports/index.html", {"request": request})


@router.get("/reports/acks", name="ui_reports_acks")
def reports_acks(request: Request):
    return templates.TemplateResponse("reports/acks.html", {"request": request})


@router.get("/reports/validate", name="ui_reports_validate")
def reports_validate(request: Request):
    return templates.TemplateResponse("reports/validate.html", {"request": request})
