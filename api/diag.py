import html as _html
from pathlib import Path
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
from api.activity_log import ACTIVITY_FILE, tail_activity_lines

router = APIRouter()
_BASE_DIR = Path(__file__).resolve().parents[1]
_HTTP_LOG = _BASE_DIR / "out" / "interop" / "server_http.log"


def _tail_file(path: Path, limit: int) -> list[str]:
    if limit <= 0:
        return []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except FileNotFoundError:
        return []
    except Exception:
        return []
    if not lines:
        return []
    return [line.rstrip("\n") for line in lines[-limit:]]

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
    try:
        limit_value = int(limit or 200)
    except (TypeError, ValueError):
        limit_value = 200
    limit_value = max(1, min(2000, limit_value))
    gen_lines = tail_debug_lines(limit_value)
    http_lines = _tail_file(_HTTP_LOG, limit_value)
    lines = (http_lines + gen_lines)[-limit_value:]
    payload = {
        "lines": lines,
        "limit": limit_value,
        "path": str(LOG_FILE),
        "http_path": str(_HTTP_LOG),
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


@router.get("/api/diag/activity")
async def get_activity(limit: int = 50, format: str = "json"):
    try:
        limit_value = int(limit or 50)
    except (TypeError, ValueError):
        limit_value = 50
    limit_value = max(1, min(1000, limit_value))
    lines = tail_activity_lines(limit_value)
    payload = {
        "lines": lines,
        "limit": limit_value,
        "path": str(ACTIVITY_FILE),
        "count": len(lines),
        "enabled": True,
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


def _choose_format(format: str | None, request: Request | None = None) -> str:
    if format:
        return (format or "json").lower()
    if request is not None:
        accept = (request.headers.get("accept") or "").lower()
        if "text/html" in accept:
            return "html"
    return "json"


def _debug_state_response(enabled: bool, fmt: str, *, action: str | None = None):
    if fmt in {"html", "htm"}:
        label = "ON" if enabled else "OFF"
        cls = "chip" + ("" if enabled else " muted")
        return HTMLResponse(f"<span id='debug-state' class='{cls}'>Debug {label}</span>")
    payload: Dict[str, Any] = {"enabled": enabled}
    if action is not None:
        payload["action"] = action
    return JSONResponse(payload)


@router.get("/api/diag/debug/state")
async def get_debug_state(format: str | None = None):
    enabled = is_debug_enabled()
    fmt = _choose_format(format)
    return _debug_state_response(enabled, fmt)


@router.post("/api/diag/debug/state/{action}")
async def mutate_debug_state(action: str, request: Request, format: str | None = None):
    action = (action or "").strip().lower()
    if action == "enable":
        set_debug_enabled(True)
    elif action == "disable":
        set_debug_enabled(False)
    elif action == "toggle":
        toggle_debug_enabled()
    else:
        raise HTTPException(status_code=400, detail="Unknown debug action")
    enabled = is_debug_enabled()
    fmt = _choose_format(format, request)
    return _debug_state_response(enabled, fmt, action=action)


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
