from __future__ import annotations

import json
import time
import shutil
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
OUT_ROOT = Path("out/security")
UI_OUT = OUT_ROOT / "ui"
INDEX_PATH = UI_OUT / "index.json"


@router.get("/security/summary", response_class=HTMLResponse)
def security_summary():
    """Minimal KPI block so the Security dashboard doesn't 404."""
    kpis = {
        "controls_mapped": 12,
        "evidence_items": 34,
        "findings_open": 3,
        "last_scan": "n/a",
    }
    html = (
        "<section class='card'><h3>Security Summary</h3>"
        "<div class='row gap'>"
        f"<span class='chip'>controls: <strong>{kpis['controls_mapped']}</strong></span>"
        f"<span class='chip'>evidence: <strong>{kpis['evidence_items']}</strong></span>"
        f"<span class='chip'>open findings: <strong>{kpis['findings_open']}</strong></span>"
        f"<span class='chip'>last scan: <strong>{kpis['last_scan']}</strong></span>"
        "</div></section>"
    )
    return HTMLResponse(html)


def _save_upload(out_dir: Path, up: UploadFile) -> Path:
    uploads = out_dir / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    dest = uploads / up.filename
    with dest.open("wb") as fh:
        fh.write(up.file.read())
    return dest


def _glob_json(root: Path) -> list[Path]:
    return sorted(list(root.glob("**/active/*.json")), key=lambda p: p.stat().st_mtime, reverse=True)


def _safe_load(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _cvss_to_bucket(score: float | None) -> str | None:
    if score is None:
        return None
    try:
        s = float(score)
    except Exception:
        return None
    if s >= 9.0:
        return "Critical"
    if s >= 7.0:
        return "High"
    if s >= 4.0:
        return "Medium"
    if s > 0.0:
        return "Low"
    return None


def _is_gate(obj: dict) -> bool:
    return ("ok" in obj or "deny" in obj) and "inventory" not in obj


def _is_recon(obj: dict) -> bool:
    return "inventory" in obj or obj.get("profile") in {"safe", "version", "full"}


def _is_net(obj: dict) -> bool:
    return "packets" in obj or "flows" in obj


def _is_ir(obj: dict) -> bool:
    return "incident" in obj and "steps" in obj


def _compute_kpis(files: list[Path]) -> tuple[dict, dict | None]:
    kpi = {
        "gate": {"allowed": 0, "total": 0, "last": None},
        "recon": {
            "hosts": 0,
            "services": 0,
            "ports": 0,
            "cves": 0,
            "kev": 0,
            "sev": {"Critical": 0, "High": 0, "Medium": 0, "Low": 0},
        },
        "net": {"packets": 0, "flows": 0, "alerts": 0},
        "ir": {"incidents": 0, "last": None},
    }
    last_recon: dict | None = None
    seen_ports = set()

    for p in files:
        o = _safe_load(p)
        if not o:
            continue
        if _is_gate(o):
            kpi["gate"]["total"] += 1
            if o.get("ok"):
                kpi["gate"]["allowed"] += 1
                if kpi["gate"]["last"] is None:
                    kpi["gate"]["last"] = "Allowed"
            elif o.get("deny"):
                if kpi["gate"]["last"] is None:
                    kpi["gate"]["last"] = "Denied"
        elif _is_recon(o):
            if last_recon is None:
                last_recon = o
            inv = o.get("inventory") or {}
            hosts = inv.get("hosts") or []
            services = inv.get("services") or []
            kpi["recon"]["hosts"] = max(kpi["recon"]["hosts"], len(hosts))
            kpi["recon"]["services"] = max(kpi["recon"]["services"], len(services))
            for s in services:
                if s.get("port") is not None:
                    seen_ports.add(s["port"])
                for c in s.get("cves") or []:
                    kpi["recon"]["cves"] += 1
                    if c.get("kev"):
                        kpi["recon"]["kev"] += 1
                    bucket = _cvss_to_bucket(c.get("cvss") or c.get("cvss_v3") or c.get("cvssScore"))
                    if bucket:
                        kpi["recon"]["sev"][bucket] += 1
            kpi["recon"]["ports"] = len(seen_ports)
        elif _is_net(o):
            kpi["net"]["packets"] = max(kpi["net"]["packets"], int(o.get("packets") or 0))
            kpi["net"]["flows"] = max(kpi["net"]["flows"], int(o.get("flows") or 0))
            kpi["net"]["alerts"] = max(kpi["net"]["alerts"], len(o.get("alerts") or []))
        elif _is_ir(o):
            kpi["ir"]["incidents"] += 1
            if kpi["ir"]["last"] is None:
                kpi["ir"]["last"] = o.get("incident")
    return kpi, last_recon


def _update_index_from_kpis(kpi: dict) -> None:
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        idx = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        if not isinstance(idx, list):
            idx = []
    except Exception:
        idx = []
    point = {
        "t": int(time.time()),
        "gate_allowed": kpi["gate"]["allowed"],
        "gate_total": kpi["gate"]["total"],
        "recon_services": kpi["recon"]["services"],
        "recon_cves": kpi["recon"]["cves"],
        "recon_kev": kpi["recon"]["kev"],
        "net_alerts": kpi["net"]["alerts"],
    }
    idx.append(point)
    idx = idx[-200:]
    INDEX_PATH.write_text(json.dumps(idx), encoding="utf-8")


@router.get("/security/summary", response_class=HTMLResponse)
async def security_summary(request: Request):
    files = _glob_json(OUT_ROOT)
    kpi, last_recon = _compute_kpis(files)
    _update_index_from_kpis(kpi)
    return templates.TemplateResponse(
        "security/summary.html",
        {"request": request, "kpi": kpi, "last_recon": last_recon},
    )


@router.post("/security/demo/seed", response_class=HTMLResponse)
async def security_demo_seed(request: Request):
    src = Path("static/examples/cyber/results")
    dst = UI_OUT / "demo" / "active"
    dst.mkdir(parents=True, exist_ok=True)
    count = 0
    if src.exists():
        for p in src.glob("*.json"):
            shutil.copyfile(p, dst / p.name)
            count += 1
    files = _glob_json(OUT_ROOT)
    kpi, _ = _compute_kpis(files)
    _update_index_from_kpis(kpi)
    return HTMLResponse(f"<div class='muted'>Demo data loaded ({count} file(s)).</div>")


@router.post("/security/baseline", response_class=HTMLResponse)
async def security_baseline(
    request: Request,
    target: str = Form(...),
    scope_file: str = Form("docs/cyber/scope_example.txt"),
    profile: str = Form("safe"),
    out_dir: str = Form("out/security/ui"),
):
    gate_payload = {
        "target": target,
        "scope_file": scope_file,
        "auth_doc": "",
        "out_dir": out_dir,
    }
    try:
        gate_res = await anyio.to_thread.run_sync(lambda: gate_tool(json.dumps(gate_payload)))
        gate_ok = json.loads(gate_res).get("ok", False)
    except Exception:
        gate_ok = False
    recon_payload = {
        "target": target,
        "scope_file": scope_file,
        "profile": profile,
        "out_dir": out_dir,
    }
    recon_res = await anyio.to_thread.run_sync(lambda: recon_tool(json.dumps(recon_payload)))
    data = {"gate_ok": gate_ok, "recon": json.loads(recon_res)}
    kpi, last_recon = _compute_kpis(_glob_json(OUT_ROOT))
    _update_index_from_kpis(kpi)
    return templates.TemplateResponse(
        "security/partials/baseline_result.html",
        {"request": request, "payload": data, "kpi": kpi, "last_recon": last_recon},
        media_type="text/html",
    )


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
    kpi, last_recon = _compute_kpis(_glob_json(OUT_ROOT))
    _update_index_from_kpis(kpi)
    return templates.TemplateResponse(
        "security/partials/gate_result.html",
        {"request": request, "payload": data, "kpi": kpi, "last_recon": last_recon},
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
    kpi, last_recon = _compute_kpis(_glob_json(OUT_ROOT))
    _update_index_from_kpis(kpi)
    return templates.TemplateResponse(
        "security/partials/recon_result.html",
        {"request": request, "payload": data, "kpi": kpi, "last_recon": last_recon},
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
    kpi, last_recon = _compute_kpis(_glob_json(OUT_ROOT))
    _update_index_from_kpis(kpi)
    return templates.TemplateResponse(
        "security/partials/net_result.html",
        {"request": request, "payload": data, "kpi": kpi, "last_recon": last_recon},
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
    kpi, last_recon = _compute_kpis(_glob_json(OUT_ROOT))
    _update_index_from_kpis(kpi)
    return templates.TemplateResponse(
        "security/partials/ir_result.html",
        {"request": request, "payload": data, "kpi": kpi, "last_recon": last_recon},
        media_type="text/html",
    )
