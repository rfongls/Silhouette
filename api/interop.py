from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel

from skills.hl7_drafter import draft_message, send_message

router = APIRouter()


class HL7Request(BaseModel):
    message_type: str
    json_data: dict | None = None
    host: str
    port: int


@router.post("/interop/hl7/draft-send")
async def interop_hl7_send(req: HL7Request):
    data = req.json_data or {}
    message = draft_message(req.message_type, data)
    ack = await send_message(req.host, req.port, message)
    return {"message": message, "ack": ack}


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
    return result


@router.post("/interop/validate")
async def validate_fhir(
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
    return result
