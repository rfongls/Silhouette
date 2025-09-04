from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, File, Form, Request
from fastapi.responses import PlainTextResponse, HTMLResponse
from starlette.templating import Jinja2Templates

from skills.hl7_drafter import draft_message, send_message

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.post("/interop/hl7/draft-send")
async def interop_hl7_send(
    message_type: str = Form(...),
    json_data: str = Form("{}"),
    host: str = Form(...),
    port: int = Form(...),
):
    try:
        data = json.loads(json_data) if json_data.strip() else {}
    except json.JSONDecodeError as e:
        return PlainTextResponse(
            json.dumps({"ok": False, "error": f"Invalid JSON for json_data: {e}"}, indent=2),
            media_type="application/json",
        )
    message = draft_message(message_type, data)
    ack = await send_message(host, port, message)
    return PlainTextResponse(
        json.dumps({"message": message, "ack": ack}, indent=2),
        media_type="application/json",
    )

def _run_cli(args: List[str]) -> dict:
    proc = subprocess.run(
        ["python", "-m", "silhouette_core.cli", *args],
        capture_output=True,
        text=True,
    )
    return {
        "rc": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


@router.post("/interop/translate")
async def translate(
    request: Request,
    hl7_file: UploadFile = File(...),
    bundle: str = Form("transaction"),
    validate: bool = Form(False),
    out_dir: str = Form("out/interop/ui"),
):
    out_path = Path(out_dir)
    uploads = out_path / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    src = uploads / hl7_file.filename
    with src.open("wb") as fh:
        fh.write(hl7_file.file.read())
    args = ["fhir", "translate", "--in", str(src), "--bundle", bundle, "--out", out_dir]
    if validate:
        args.append("--validate")
    result = _run_cli(args)
    result["out"] = out_dir
    return templates.TemplateResponse(
        "interop/partials/translate_result.html",
        {"request": request, "result": result},
        media_type="text/html",
    )


@router.post("/interop/validate")
async def validate_fhir(
    request: Request,
    fhir_files: List[UploadFile] = File(...),
    out_dir: str = Form("out/interop/ui"),
):
    in_dir = Path(out_dir) / "uploads"
    in_dir.mkdir(parents=True, exist_ok=True)
    for up in fhir_files:
        dest = in_dir / up.filename
        with dest.open("wb") as fh:
            fh.write(up.file.read())
    args = ["fhir", "validate", "--in-dir", str(in_dir)]
    result = _run_cli(args)
    result["out"] = out_dir
    return templates.TemplateResponse(
        "interop/partials/validate_result.html",
        {"request": request, "result": result},
        media_type="text/html",
    )
