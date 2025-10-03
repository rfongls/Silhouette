import html as _html
from pathlib import Path
from typing import Any, Dict
from urllib.parse import quote_plus
from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from starlette.templating import Jinja2Templates

from api.debug_log import (
    LOG_FILE,
    is_debug_enabled,
    log_debug_event,
    log_debug_message,
    set_debug_enabled,
    tail_debug_lines,
)
from api.activity_log import ACTIVITY_FILE, tail_activity_lines

router = APIRouter()
templates = Jinja2Templates(directory="templates")
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
async def get_debug_logs(request: Request, limit: int = 200, format: str = "json"):
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
        root = request.scope.get("root_path", "")
        target = request.query_params.get("target") or "interop-debug-log"
        hx_url = f"{root}/api/diag/logs?format=html&limit={limit_value}"
        if target:
            hx_url += f"&target={quote_plus(target)}"
        return HTMLResponse(
            "<pre id='{}' class='codepane small mt scrollbox' "
            "hx-get='{}' hx-trigger='load, every 8s' hx-target='this' "
            "hx-swap='outerHTML'>{}</pre>".format(
                _html.escape(target), _html.escape(hx_url), escaped
            )
        )
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


_DEFAULT_BADGE_ID = "debug-state-badge"


def _normalize_target(target: str | None) -> str:
    candidate = (target or _DEFAULT_BADGE_ID).strip()
    return candidate or _DEFAULT_BADGE_ID


async def _resolve_target_id(request: Request) -> str:
    target_param = request.query_params.get("target")
    if target_param:
        return _normalize_target(target_param)
    if request.method in {"POST", "PUT", "PATCH"}:
        try:
            form = await request.form()
        except Exception:
            form = None
        if form is not None:
            form_target = form.get("target")
            if form_target:
                return _normalize_target(form_target)
    return _DEFAULT_BADGE_ID


def _badge_template_response(request: Request, enabled: bool, target_id: str):
    context = {"request": request, "enabled": enabled, "target_id": target_id}
    return templates.TemplateResponse(
        "diag/_debug_badge.html",
        context,
        headers={"Cache-Control": "no-store"},
    )


async def _debug_state_response(
    request: Request,
    enabled: bool,
    format: str | None,
    *,
    action: str | None = None,
):
    fmt = _choose_format(format, request)
    if fmt in {"html", "htm"}:
        target_id = await _resolve_target_id(request)
        return _badge_template_response(request, enabled, target_id)
    payload: Dict[str, Any] = {"enabled": enabled}
    if action is not None:
        payload["action"] = action
    return JSONResponse(payload)


@router.get("/api/diag/debug/state/snippet")
async def get_debug_toggle_snippet(request: Request, target: str = "interop-debug-log"):
    """Return the toggle button HTML snippet. Used by UI pages via HTMX."""
    enabled = is_debug_enabled()
    target_id = _normalize_target(target)
    return _badge_template_response(request, enabled, target_id)


@router.get("/api/diag/debug/state", name="api_diag_debug_state")
async def get_debug_state(request: Request, format: str | None = None):
    enabled = is_debug_enabled()
    return await _debug_state_response(request, enabled, format)


@router.post("/api/diag/debug/state/enable", name="api_diag_debug_enable")
async def api_diag_debug_enable(request: Request, format: str | None = None):
    set_debug_enabled(True)
    enabled = is_debug_enabled()
    return await _debug_state_response(request, enabled, format, action="enable")


@router.post("/api/diag/debug/state/disable", name="api_diag_debug_disable")
async def api_diag_debug_disable(request: Request, format: str | None = None):
    set_debug_enabled(False)
    enabled = is_debug_enabled()
    return await _debug_state_response(request, enabled, format, action="disable")


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
