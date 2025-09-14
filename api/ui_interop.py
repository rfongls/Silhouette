from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from starlette.templating import Jinja2Templates
from api.interop_gen import generate_messages, parse_any_request
from silhouette_core.interop.deid import deidentify_message
from silhouette_core.interop.validate_workbook import validate_message

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/ui/interop/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("ui/interop/skills.html", {"request": request})


@router.get("/ui/interop/skills", response_class=HTMLResponse)
async def interop_skills(request: Request):
    return templates.TemplateResponse("ui/interop/skills.html", {"request": request})


@router.get("/ui/interop/pipeline", response_class=HTMLResponse)
async def interop_pipeline(request: Request):
    return templates.TemplateResponse("ui/interop/pipeline.html", {"request": request})


@router.get("/ui/interop/history", response_class=HTMLResponse)
async def history(request: Request):
    root = Path("out/interop")
    files = sorted(root.glob("*/active/*.json"), reverse=True)
    items = [p.as_posix() for p in files]
    return templates.TemplateResponse("interop/history.html", {"request": request, "items": items})


@router.get("/ui/interop/history/view")
async def history_view(path: str):
    base = Path("out").resolve()
    p = Path(path)
    try:
        target = p.resolve()
    except FileNotFoundError:
        raise HTTPException(404)
    if not target.is_file() or not str(target).startswith(str(base)):
        raise HTTPException(404)
    return PlainTextResponse(target.read_text(encoding="utf-8"), media_type="application/json")


# Pure-HTML fallback: when JS is disabled, the form posts here and we render a page.
@router.post("/ui/interop/generate", response_class=HTMLResponse)
async def ui_generate(request: Request):
    body = await parse_any_request(request)
    resp = generate_messages(body)
    text = resp.body.decode("utf-8") if hasattr(resp, "body") else str(resp)
    return templates.TemplateResponse(
        "ui/interop/generate_result.html",
        {"request": request, "hl7_text": text}
    )

# De-identify (HTML fragment suitable for hx-swap)
@router.post("/ui/interop/deidentify", response_class=HTMLResponse)
async def ui_deidentify(request: Request):
    body = await parse_any_request(request)
    text = (body.get("text") or "").strip()
    seed = body.get("seed")
    try:
        seed_int = int(seed) if seed not in (None, "") else None
    except Exception:
        seed_int = None
    if not text:
        return HTMLResponse("<div class='muted'>No input.</div>")
    out = deidentify_message(text, seed=seed_int)
    return HTMLResponse(f"<pre class='codepane'>{out}</pre>")

# Validate (HTML fragment suitable for hx-swap)
@router.post("/ui/interop/validate", response_class=HTMLResponse)
async def ui_validate(request: Request):
    body = await parse_any_request(request)
    text = body.get("text", "")
    profile = body.get("profile")
    res = validate_message(text, profile=profile)
    errs = "".join(f"<li>{e.get('message','')}</li>" for e in (res.get('errors') or []))
    warns = "".join(f"<li class='muted'>{w.get('message','')}</li>" for w in (res.get('warnings') or []))
    html = f"""
      <div class='mt'><strong>Analyze</strong> {('<span class="chip">OK</span>' if res.get('ok') else '<span class="chip">Issues</span>')}
        <div class='grid2'>
          <div><em>Errors</em><ul>{errs or '<li>None</li>'}</ul></div>
          <div><em>Warnings</em><ul class='muted'>{warns or '<li>None</li>'}</ul></div>
        </div>
      </div>
    """
    return HTMLResponse(html)

