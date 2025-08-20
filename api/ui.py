from __future__ import annotations
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from starlette.templating import Jinja2Templates
from pathlib import Path
import json, yaml

from skills.hl7_drafter import draft_message, send_message

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def _load_targets():
    p = Path("config/hosts.yaml")
    if p.exists():
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        return data.get("targets", {})
    return {}

MESSAGE_TYPES = [
    "VXU^V04","RDE^O11","ORM^O01","OML^O21","ORU^R01:RAD","MDM^T02","ADT^A01","SIU^S12","DFT^P03"
]

@router.get("/ui/hl7", response_class=HTMLResponse)
async def get_form(request: Request):
    return templates.TemplateResponse(
        "ui/hl7_send.html",
        {"request": request, "targets": _load_targets(), "message_types": MESSAGE_TYPES}
    )

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

    return templates.TemplateResponse(
        "ui/hl7_send.html",
        {
            "request": request,
            "targets": _load_targets(),
            "message_types": MESSAGE_TYPES,
            "selected_type": message_type,
            "selected_host": host,
            "selected_port": port,
            "json_data": json_data,
            "result": result,
            "error": error,
        }
    )
