from __future__ import annotations
import json
from pathlib import Path
import anyio
from fastapi import APIRouter, UploadFile, File, Form, Query, Request
from fastapi.responses import PlainTextResponse, StreamingResponse, HTMLResponse
from starlette.templating import Jinja2Templates
from skills.cyber_pentest_gate.v1.wrapper import tool as gate_tool
from skills.cyber_recon_scan.v1.wrapper import tool as recon_tool
from skills.cyber_netforensics.v1.wrapper import tool as net_tool
from skills.cyber_ir_playbook.v1.wrapper import tool as ir_tool

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _save_upload(out_dir: Path, up: UploadFile) -> Path:
    uploads = out_dir / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    dest = uploads / up.filename
    with dest.open("wb") as fh:
        fh.write(up.file.read())
    return dest


@router.post("/security/gate")
async def gate(
    request: Request,
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
    # Render a compact summary + raw JSON
    return templates.TemplateResponse(
        "security/partials/gate_result.html",
        {"request": request, "payload": data},
        media_type="text/html",
    )

@router.post("/security/recon")
async def recon(
    request: Request,
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
    return templates.TemplateResponse(
        "security/partials/recon_result.html",
        {
            "request": request,
            "payload": data,
        },
        media_type="text/html",
    )


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
        # Offload synchronous work so we don't block the event loop
        res = await anyio.to_thread.run_sync(lambda: recon_tool(json.dumps(payload)))
        yield f"data: {res}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.get("/security/recon-bulk-stream")
async def recon_bulk_stream(
    targets: str = Query(..., description="line-separated targets"),
    scope_file: str = Query("docs/cyber/scope_example.txt"),
    profile: str = Query("safe"),
    out_dir: str = Query("out/security/ui"),
):
    """
    SSE stream that processes multiple targets sequentially.
    Each target is one recon() call, and we emit progress lines as JSON strings.
    """
    target_list = [t.strip() for t in targets.splitlines() if t.strip()]

    async def event_gen():
        yield f"data: {json.dumps({'event':'start','count':len(target_list)})}\n\n"
        for idx, tgt in enumerate(target_list, 1):
            payload = {
                "target": tgt,
                "scope_file": scope_file,
                "profile": profile,
                "out_dir": out_dir,
            }
            try:
                res = await anyio.to_thread.run_sync(lambda: recon_tool(json.dumps(payload)))
                yield f"data: {json.dumps({'event':'item','index':idx,'target':tgt,'result':json.loads(res)})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'event':'error','index':idx,'target':tgt,'error':str(e)})}\n\n"
        yield "data: {\"event\":\"done\"}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")
  
    async def event_gen():
        yield f"data: {json.dumps({'event':'start','count':len(target_list)})}\n\n"
        for idx, tgt in enumerate(target_list, 1):
            payload = {
                "target": tgt,
                "scope_file": scope_file,
                "profile": profile,
                "out_dir": out_dir,
            }
            try:
                res = recon_tool(json.dumps(payload))
                yield f"data: {json.dumps({'event':'item','index':idx,'target':tgt,'result':json.loads(res)})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'event':'error','index':idx,'target':tgt,'error':str(e)})}\n\n"
        yield "data: {\"event\":\"done\"}\n\n"
    return StreamingResponse(event_gen(), media_type="text/event-stream")
    return StreamingResponse(event_gen(), media_type="text/event-stream")

@router.post("/security/netforensics")
async def netforensics(
    request: Request,
    pcap: UploadFile = File(...),
    out_dir: str = Form("out/security/ui"),
):
    out_path = Path(out_dir)
    pcap_path = _save_upload(out_path, pcap)
    payload = {"pcap": str(pcap_path), "out_dir": out_dir}
    res = net_tool(json.dumps(payload))
    data = json.loads(res)
    return templates.TemplateResponse(
        "security/partials/net_result.html",
        {
            "request": request,
            "payload": data,
        },
        media_type="text/html",
    )


@router.post("/security/ir")
async def ir(
    request: Request,
    incident: str = Form(...),
    out_dir: str = Form("out/security/ui"),
):
    payload = {"incident": incident, "out_dir": out_dir}
    res = ir_tool(json.dumps(payload))
    data = json.loads(res)
    return templates.TemplateResponse(
        "security/partials/ir_result.html",
        {"request": request, "payload": data},
        media_type="text/html",
    )
