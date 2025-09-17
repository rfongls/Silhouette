import html as _html
from typing import Any, Dict
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

from api.debug_log import (
    LOG_FILE,
    is_debug_enabled,
    log_debug_event,
    log_debug_message,
    set_debug_enabled,
    tail_debug_lines,
    toggle_debug_enabled,
)

router = APIRouter()

@router.post("/api/diag/echo")
async def echo(request: Request):
    raw = await request.body()
    try:
        parsed_json = await request.json()
    except Exception:
        parsed_json = None
    form_data = None
    try:
        f = await request.form()
        form_data = {k: f.get(k) for k in f}
    except Exception:
        pass
    return JSONResponse({
        "method": request.method,
        "path": request.url.path,
        "content_type": request.headers.get("content-type"),
        "accept": request.headers.get("accept"),
        "hx": request.headers.get("hx-request"),
        "raw_len": len(raw or b""),
        "json": parsed_json,
        "form": form_data,
        "query": dict(request.query_params),
    })


@router.get("/api/diag/routes")
async def list_routes(request: Request):
    app: FastAPI = request.app
    out = []
    for r in app.routes:
        try:
            name = getattr(r, "name", None)
            path = getattr(r, "path", None)
            methods = list(getattr(r, "methods", []) or [])
            if path:
                out.append({"name": name, "path": path, "methods": methods})
        except Exception:
            pass
    out.sort(key=lambda x: (x["path"], ",".join(x["methods"])))
    return JSONResponse({"routes": out})


@router.get("/api/diag/logs")
async def get_debug_logs(limit: int = 200, format: str = "json"):
    lines = tail_debug_lines(limit)
    payload = {
        "lines": lines,
        "limit": limit,
        "path": str(LOG_FILE),
        "count": len(lines),
        "enabled": is_debug_enabled(),
    }
    fmt = (format or "json").lower()
    if fmt in {"html", "htm"}:
        escaped = "\n".join(_html.escape(line) for line in lines)
        return HTMLResponse(f"<pre class='scrollbox small'>{escaped}</pre>")
    if fmt in {"text", "plain", "txt"}:
        text = "\n".join(lines)
        if text:
            text += "\n"
        return PlainTextResponse(text or "", media_type="text/plain")
    return JSONResponse(payload)


def _coerce_payload(data: Any) -> Dict[str, Any]:
    if isinstance(data, dict):
        return {k: v for k, v in data.items()}
    return {}


async def _extract_payload(request: Request) -> Dict[str, Any]:
    body: Dict[str, Any] = {}
    try:
        parsed = await request.json()
        body = _coerce_payload(parsed)
    except Exception:
        body = {}
    if not body:
        try:
            form = await request.form()
            body = {k: form.get(k) for k in form}
        except Exception:
            body = {}
    if not body:
        body = dict(request.query_params)
    return body


@router.get("/api/diag/debug/state")
async def get_debug_state():
    return JSONResponse({"enabled": is_debug_enabled()})


@router.post("/api/diag/debug/state/{action}")
async def mutate_debug_state(action: str):
    action = (action or "").strip().lower()
    if action == "enable":
        set_debug_enabled(True)
    elif action == "disable":
        set_debug_enabled(False)
    elif action == "toggle":
        toggle_debug_enabled()
    else:
        raise HTTPException(status_code=400, detail="Unknown debug action")
    return JSONResponse({"enabled": is_debug_enabled(), "action": action})


@router.post("/api/diag/debug/event")
async def capture_debug_event(request: Request):
    payload = await _extract_payload(request)
    event = (
        payload.pop("event", None)
        or payload.pop("name", None)
        or payload.pop("action", None)
        or "ui-event"
    )
    event = str(event).strip() or "ui-event"
    detail = payload.pop("detail", None)
    if detail is not None and "details" not in payload:
        payload["details"] = detail
    recorded = log_debug_event(f"ui.{event}", **payload)
    # provide a hint even when disabled
    if not recorded and is_debug_enabled():
        log_debug_message(f"ui.{event} (dropped)")
    return JSONResponse({"ok": recorded, "enabled": is_debug_enabled(), "event": event})
