from __future__ import annotations

import json
import subprocess
import time
import shutil
from pathlib import Path
from typing import List
import re
from fastapi import APIRouter, UploadFile, File, Form, Request
from fastapi.responses import PlainTextResponse, HTMLResponse
from starlette.templating import Jinja2Templates

from skills.hl7_drafter import draft_message, send_message

router = APIRouter()
templates = Jinja2Templates(directory="templates")
OUT_ROOT = Path("out/interop")
UI_OUT = OUT_ROOT / "ui"
INDEX_PATH = UI_OUT / "index.json"


def _write_artifact(kind: str, data: dict) -> Path:
    data = {"kind": kind, **data}
    p = UI_OUT / kind / "active" / f"{int(time.time())}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return p


@router.post("/interop/hl7/draft-send")
async def interop_hl7_send(
    request: Request,
    message_type: str = Form(...),
    json_data: str = Form("{}"),
    host: str = Form(...),
    port: int = Form(...),
):
    try:
        data = json.loads(json_data) if json_data.strip() else {}
    except json.JSONDecodeError as e:
        payload = {"ok": False, "error": f"Invalid JSON for json_data: {e}"}
        _write_artifact("send", payload)
        return templates.TemplateResponse(
            "interop/partials/draft_result.html",
            {"request": request, "payload": payload, "kpi": _compute_kpis()},
            media_type="text/html",
        )
    message = draft_message(message_type, data)
    ack = await send_message(host, port, message)
    msa_aa = bool(re.search(r"(^|\\r|\\n)MSA\\|AA(\\||$)", ack or ""))
    payload = {
        "message_type": message_type,
        "message": message,
        "ack": ack,
        "ack_ok": msa_aa,
    }
    _write_artifact("send", payload)
    return templates.TemplateResponse(
        "interop/partials/draft_result.html",
        {"request": request, "payload": payload, "kpi": _compute_kpis()},
        media_type="text/html",
    )


def _run_cli(args: List[str]) -> dict:
    proc = subprocess.run(
        ["python", "-m", "silhouette_core.cli", *args],
        capture_output=True,
        text=True,
    )
    return {"rc": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


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
    _write_artifact("translate", result)
    return templates.TemplateResponse(
        "interop/partials/translate_result.html",
        {"request": request, "result": result, "kpi": _compute_kpis()},
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
    _write_artifact("validate", result)
    return templates.TemplateResponse(
        "interop/partials/validate_result.html",
        {"request": request, "result": result, "kpi": _compute_kpis()},
        media_type="text/html",
    )


# ---------- KPI Summary, Demo & Quickstart ----------

def _compute_kpis() -> dict:
    files = sorted(list(OUT_ROOT.glob("**/active/*.json")), key=lambda p: p.stat().st_mtime, reverse=True)
    k = {
        "send": {"count": 0, "ok": 0, "last_ok": None},
        "translate": {"ok": 0, "fail": 0},
        "validate": {"ok": 0, "fail": 0},
    }
    for p in files:
        o = json.loads(p.read_text(encoding="utf-8"))
        if "ack" in o or "ack_ok" in o:
            k["send"]["count"] += 1
            ok = bool(o.get("ack_ok"))
            if ok:
                k["send"]["ok"] += 1
            if k["send"]["last_ok"] is None:
                k["send"]["last_ok"] = ok
        elif "stdout" in o and "stderr" in o and "rc" in o:
            kind = o.get("kind")
            ok = int(o.get("rc", 1)) == 0
            if kind == "translate":
                if ok:
                    k["translate"]["ok"] += 1
                else:
                    k["translate"]["fail"] += 1
            elif kind == "validate":
                if ok:
                    k["validate"]["ok"] += 1
                else:
                    k["validate"]["fail"] += 1
            else:
                if "translate" in str(p.parent.parent):
                    if ok:
                        k["translate"]["ok"] += 1
                    else:
                        k["translate"]["fail"] += 1
                else:
                    if ok:
                        k["validate"]["ok"] += 1
                    else:
                        k["validate"]["fail"] += 1
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        idx = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        if not isinstance(idx, list):
            idx = []
    except Exception:
        idx = []
    idx.append({
        "t": int(time.time()),
        "send_ok": k["send"]["ok"],
        "translate_ok": k["translate"]["ok"],
        "validate_ok": k["validate"]["ok"],
    })
    idx = idx[-200:]
    INDEX_PATH.write_text(json.dumps(idx), encoding="utf-8")
    return k


@router.get("/interop/summary", response_class=HTMLResponse)
async def interop_summary(request: Request):
    return templates.TemplateResponse("interop/summary.html", {"request": request, "kpi": _compute_kpis()})


@router.post("/interop/demo/seed", response_class=HTMLResponse)
async def interop_demo_seed(request: Request):
    src = Path("static/examples/interop/results")
    dst = UI_OUT / "demo" / "active"
    dst.mkdir(parents=True, exist_ok=True)
    if src.exists():
        for p in src.glob("*.json"):
            shutil.copyfile(p, dst / p.name)
    return HTMLResponse("<div class='muted'>Interop demo results loaded.</div>")


@router.post("/interop/quickstart", response_class=HTMLResponse)
async def interop_quickstart(request: Request, trigger: str = Form("VXU_V04")):
    examples = Path("static/examples/hl7/json")
    js = examples / f"{trigger}_min.json"
    if not js.exists():
        return HTMLResponse(f"<div class='muted'>No example for {trigger}</div>")
    data = json.loads(js.read_text(encoding="utf-8"))
    hl7 = draft_message(trigger, data)
    hl7_path = UI_OUT / "quickstart" / "active" / f"{int(time.time())}.hl7"
    hl7_path.parent.mkdir(parents=True, exist_ok=True)
    hl7_path.write_text(hl7, encoding="utf-8")
    tr = _run_cli(["fhir", "translate", "--in", str(hl7_path), "--bundle", "transaction", "--out", str(UI_OUT)])
    _write_artifact("translate", {**tr, "out": str(UI_OUT)})
    va = _run_cli(["fhir", "validate", "--in-dir", str(UI_OUT)])
    _write_artifact("validate", va)
    return templates.TemplateResponse(
        "interop/partials/pipeline_result.html",
        {
            "request": request,
            "trigger": trigger,
            "hl7_path": str(hl7_path),
            "translate": tr,
            "validate": va,
            "kpi": _compute_kpis(),
        },
        media_type="text/html",
    )
