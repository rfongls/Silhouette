from __future__ import annotations

import json
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, Query
from fastapi.responses import PlainTextResponse, StreamingResponse


from skills.cyber_pentest_gate.v1.wrapper import tool as gate_tool
from skills.cyber_recon_scan.v1.wrapper import tool as recon_tool
from skills.cyber_netforensics.v1.wrapper import tool as net_tool
from skills.cyber_ir_playbook.v1.wrapper import tool as ir_tool

router = APIRouter()


def _save_upload(out_dir: Path, up: UploadFile) -> Path:
    uploads = out_dir / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    dest = uploads / up.filename
    with dest.open("wb") as fh:
        fh.write(up.file.read())
    return dest


@router.post("/security/gate")
async def gate(
    target: str = Form(...),
    scope_file: str = Form("docs/cyber/scope_example.txt"),
    auth_doc: UploadFile = File(...),
    out_dir: str = Form("out/security/ui"),
):
    out_path = Path(out_dir)
    auth_path = _save_upload(out_path, auth_doc)
    payload = {
        "target": target,
        "scope_file": scope_file,
        "auth_doc": str(auth_path),
        "out_dir": out_dir,
    }
    res = gate_tool(json.dumps(payload))
    data = json.loads(res)
    return PlainTextResponse(json.dumps(data, indent=2), media_type="application/json")

@router.post("/security/recon")
async def recon(
    target: str = Form(...),
    scope_file: str = Form("docs/cyber/scope_example.txt"),
    profile: str = Form("safe"),
    out_dir: str = Form("out/security/ui"),
):
    payload = {
        "target": target,
        "scope_file": scope_file,
        "profile": profile,
        "out_dir": out_dir,
    }
    res = recon_tool(json.dumps(payload))
    data = json.loads(res)
    return PlainTextResponse(json.dumps(data, indent=2), media_type="application/json")

@router.get("/security/recon-stream")
async def recon_stream(
    target: str = Query(...),
    scope_file: str = Query("docs/cyber/scope_example.txt"),
    profile: str = Query("safe"),
    out_dir: str = Query("out/security/ui"),
):
    """SSE stream (GET) to support EventSource() in the UI."""

    async def event_gen():
        yield "data: started\n\n"
        payload = {
            "target": target,
            "scope_file": scope_file,
            "profile": profile,
            "out_dir": out_dir,
        }
        res = recon_tool(json.dumps(payload))
        yield f"data: {res}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.post("/security/netforensics")
async def netforensics(
    pcap: UploadFile = File(...),
    out_dir: str = Form("out/security/ui"),
):
    out_path = Path(out_dir)
    pcap_path = _save_upload(out_path, pcap)
    payload = {"pcap": str(pcap_path), "out_dir": out_dir}
    res = net_tool(json.dumps(payload))
    data = json.loads(res)
    return PlainTextResponse(json.dumps(data, indent=2), media_type="application/json")


@router.post("/security/ir")
async def ir(
    incident: str = Form(...),
    out_dir: str = Form("out/security/ui"),
):
    payload = {"incident": incident, "out_dir": out_dir}
    res = ir_tool(json.dumps(payload))
    data = json.loads(res)
    return PlainTextResponse(json.dumps(data, indent=2), media_type="application/json")
