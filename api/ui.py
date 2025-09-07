from __future__ import annotations

import json
from pathlib import Path

import yaml
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.templating import Jinja2Templates

from skills.hl7_drafter import draft_message, send_message

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", include_in_schema=False)
def root():
    # Default entry → Reports Home
    return RedirectResponse("/ui/home", status_code=307)


@router.get("/ui/home", response_class=HTMLResponse)
def ui_home(request: Request):
    """
    Reports Home — high-level KPIs and recent activity.
    Uses HTMX to pull skill-specific summaries.
    """
    return templates.TemplateResponse("ui/home_reports.html", {"request": request})


@router.get("/ui/skills", response_class=HTMLResponse)
def ui_skills_index(request: Request):
    """
    Skills Index — navigate to skill dashboards (Interop, Security, etc.).
    """
    skills = [
        {
            "name": "Interoperability",
            "href": "/ui/interop/dashboard",
            "desc": "Generate/de-ID/validate HL7, translate to FHIR, and transport via MLLP.",
        },
        {
            "name": "Security",
            "href": "/ui/security/dashboard",
            "desc": "Run security tools, capture evidence, and review findings.",
        },
    ]
    return templates.TemplateResponse(
        "ui/skills_index.html", {"request": request, "skills": skills}
    )

def _load_targets():
    p = Path("config/hosts.yaml")
    if p.exists():
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        return data.get("targets", {})
    return {}

MESSAGE_TYPES = [
    "VXU^V04","RDE^O11","ORM^O01","OML^O21","ORU^R01:RAD","MDM^T02","ADT^A01","SIU^S12","DFT^P03"
]

def _render(request: Request, context: dict) -> HTMLResponse:
    try:
        return templates.TemplateResponse(request, "ui/hl7_send.html", context)
    except Exception:
        context["request"] = request
        return templates.TemplateResponse("ui/hl7_send.html", context)


@router.get("/ui/hl7", response_class=HTMLResponse)
async def get_form(request: Request):
    return _render(request, {"targets": _load_targets(), "message_types": MESSAGE_TYPES})

@router.post("/ui/hl7", response_class=HTMLResponse)
async def post_form(
    request: Request,
    message_type: str = Form(...),
    json_data: str = Form(""),
    host: str = Form(...),
    port: int = Form(...),
    action: str = Form("draft")
):
    result = {"message": "", "ack": ""}
    error = None
    try:
        payload = json.loads(json_data) if json_data.strip() else {}
        message = draft_message(message_type, payload)
        result["message"] = message
        if action == "draft_send":
            result["ack"] = await send_message(host, port, message)
    except Exception as e:
        error = str(e)

    return _render(
        request,
        {
            "targets": _load_targets(),
            "message_types": MESSAGE_TYPES,
            "selected_type": message_type,
            "selected_host": host,
            "selected_port": port,
            "json_data": json_data,
            "result": result,
            "error": error,
        },
    )
