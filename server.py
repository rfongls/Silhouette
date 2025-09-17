import json
import logging
import sys
import time
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.responses import RedirectResponse, Response as StarletteResponse
from api.interop import router as interop_router
from api.interop_gen import router as interop_gen_router, try_generate_on_validation_error
from api.security import router as security_router
from api.ui import router as ui_router
from api.ui_interop import router as ui_interop_router
from api.ui_security import router as ui_security_router
from api.diag import router as diag_router

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)
http_logger = logging.getLogger("silhouette.http")

_HTTP_LOG_PATH = Path("out/interop/server_http.log")
try:
    _HTTP_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
except Exception:
    # Best-effort; the middleware still logs to the console/root logger.
    pass
if not any(getattr(h, "baseFilename", None) == str(_HTTP_LOG_PATH) for h in http_logger.handlers):
    fh = logging.FileHandler(_HTTP_LOG_PATH, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
    http_logger.addHandler(fh)
http_logger.setLevel(logging.INFO)

app = FastAPI(title="Silhouette Core Interop")
for r in (
    ui_router,
    ui_interop_router,
    ui_security_router,
    interop_gen_router,  # specific generator endpoint
    interop_router,      # generic tools (now under /api/interop/exec/{tool})
    security_router,
    diag_router,         # diagnostics
):
    app.include_router(r)
app.mount("/static", StaticFiles(directory="static"), name="static")


def _clip_bytes(data: bytes, limit: int = 2000) -> str:
    if not data:
        return ""
    text = data.decode("utf-8", errors="replace")
    if len(text) <= limit:
        return text
    return text[:limit] + f"…(+{len(text) - limit})"

_TEXTUAL_CONTENT_PREFIXES = (
    "text/",
    "application/json",
    "application/xml",
    "application/javascript",
    "application/problem+json",
)

_REDACT_KEYS = {
    "password",
    "token",
    "authorization",
    "api_key",
    "access_token",
    "refresh_token",
}


def _redact_secrets(value):
    if isinstance(value, dict):
        redacted = {}
        for key, inner in value.items():
            if key and key.lower() in _REDACT_KEYS:
                redacted[key] = "***REDACTED***"
            else:
                redacted[key] = _redact_secrets(inner)
        return redacted
    if isinstance(value, list):
        return [_redact_secrets(v) for v in value]
    return value


def _safe_json_preview(data: bytes) -> str:
    if not data:
        return ""
    try:
        parsed = json.loads(data.decode("utf-8"))
    except Exception:
        return _clip_bytes(data)
    parsed = _redact_secrets(parsed)
    try:
        return json.dumps(parsed)[:2000]
    except Exception:
        return _clip_bytes(data)


@app.middleware("http")
async def http_action_logger(request: Request, call_next):
    start = time.time()
    raw_body = await request.body()

    async def receive():
        return {"type": "http.request", "body": raw_body, "more_body": False}

    replayable_request = Request(request.scope, receive)
    action = f"{request.method} {request.url.path}"
    vars_preview = {
        "query": dict(request.query_params),
        "ctype": request.headers.get("content-type"),
        "raw_len": len(raw_body or b""),
        "body_preview": _safe_json_preview(raw_body),
    }
    http_logger.info("Action=%s Vars=%s", action, vars_preview)

    try:
        response = await call_next(replayable_request)
    except Exception:
        elapsed_ms = int(1000 * (time.time() - start))
        http_logger.exception("Action=%s Response=<exception> ms=%s", action, elapsed_ms)
        raise
    content_type = ""
    if hasattr(response, "headers") and response.headers is not None:
        content_type = response.headers.get("content-type") or ""
    lowered_ctype = content_type.lower()
    is_textual = not lowered_ctype or any(
        lowered_ctype.startswith(prefix) for prefix in _TEXTUAL_CONTENT_PREFIXES
    )
    skip_reason = None
    if request.url.path.startswith("/static"):
        skip_reason = "static"
    elif not is_textual:
        skip_reason = "binary"

    if skip_reason:
        elapsed_ms = int(1000 * (time.time() - start))
        http_logger.info(
            "Action=%s Response={status:%s, ms:%s, preview:<skipped %s>}",
            action,
            response.status_code,
            elapsed_ms,
            skip_reason,
        )
        return response

    body = b""
    if hasattr(response, "body_iterator") and response.body_iterator is not None:
        async for chunk in response.body_iterator:
            body += chunk
    elif hasattr(response, "body"):
        if isinstance(response.body, (bytes, bytearray)):
            body = bytes(response.body)
        elif isinstance(response.body, str):
            body = response.body.encode("utf-8", errors="replace")
    headers = dict(response.headers) if hasattr(response, "headers") else {}
    headers.pop("content-length", None)
    new_response = StarletteResponse(
        content=body,
        status_code=response.status_code,
        headers=headers,
        media_type=response.media_type,
        background=response.background,
    )
    elapsed_ms = int(1000 * (time.time() - start))
    http_logger.info(
        "Action=%s Response={status:%s, ms:%s, preview:%s}",
        action,
        response.status_code,
        elapsed_ms,
        _clip_bytes(body),
    )
    return new_response

def _preview_bytes(data: bytes | None, limit: int = 160) -> str:
    if not data:
        return ""
    text = data.decode("utf-8", errors="replace").replace("\r", "\\r").replace("\n", "\\n")
    if len(text) > limit:
        return f"{text[:limit]}…(+{len(text) - limit})"
    return text


@app.middleware("http")
async def _trace_requests(request: Request, call_next):
    hx = request.headers.get("hx-request")
    print(
        "[TRACE] %s %s?%s ctype=%s accept=%s hx=%s clen=%s"
        % (
            request.method,
            request.url.path,
            request.url.query or "",
            request.headers.get("content-type"),
            request.headers.get("accept"),
            hx,
            request.headers.get("content-length"),
        ),
        flush=True,
    )
    resp = await call_next(request)
    resp_body: bytes | None = None
    preview = ""
    if hasattr(resp, "body") and isinstance(resp.body, (bytes, bytearray)):
        resp_body = bytes(resp.body)
        preview = _preview_bytes(resp_body)
    elif hasattr(resp, "body") and isinstance(resp.body, str):
        resp_body = resp.body.encode("utf-8", errors="replace")
        preview = _preview_bytes(resp_body)
    else:
        preview = "<stream>"
    print(
        "[TRACE] -> %s %s bytes=%s ctype=%s preview=%s"
        % (
            resp.status_code,
            request.url.path,
            len(resp_body) if resp_body is not None else "stream",
            resp.headers.get("content-type"),
            preview,
        ),
        flush=True,
    )
    return resp


@app.on_event("startup")
async def _route_sanity_check():
    """
    Enforce: no legacy /api/interop/{...} routes; /api/interop/generate present.
    Also dump interop routes with registration order for quick diagnosis.
    """
    interop_routes = []
    generate_get = generate_post = None
    legacy_param_routes = []
    for idx, r in enumerate(app.routes):
        path = getattr(r, "path", None)
        methods = getattr(r, "methods", set()) or set()
        if not path or not path.startswith("/api/interop"):
            continue
        ep = getattr(r, "endpoint", None)
        mod = getattr(ep, "__module__", "?")
        name = getattr(ep, "__name__", "?")
        print(f"[ROUTE]#{idx} {methods} {path} -> {mod}.{name}", file=sys.stderr)
        interop_routes.append((idx, path, methods, mod, name))
        if path == "/api/interop/generate":
            if "GET" in methods:
                generate_get = idx
            if "POST" in methods:
                generate_post = idx
        if path.startswith("/api/interop/") and "{" in path and not path.startswith("/api/interop/exec/"):
            legacy_param_routes.append((idx, path, methods, mod, name))

    if legacy_param_routes:
        details = ", ".join(f"#{i}:{p}" for i, p, *_ in legacy_param_routes)
        raise RuntimeError(
            f"Legacy dynamic route(s) still present: {details}. "
            f"All catch-all tools must live under /api/interop/exec/{{tool}}."
        )
    if generate_get is None or generate_post is None:
        raise RuntimeError("Missing GET/POST /api/interop/generate route.")

    # Soft check: ensure UI fallback route exists for no-JS submissions
    ui_gen_present = False
    for r in app.routes:
        path = getattr(r, "path", None)
        methods = getattr(r, "methods", set()) or set()
        if path == "/ui/interop/generate" and "POST" in methods:
            ui_gen_present = True
            break
    if not ui_gen_present:
        print(
            "[WARN] POST /ui/interop/generate missing — HTML (no-JS) fallback will 404; HTMX/API path still works.",
            file=sys.stderr,
        )


@app.exception_handler(RequestValidationError)
async def _log_request_validation(request: Request, exc: RequestValidationError):
    fallback = await try_generate_on_validation_error(request, exc)
    if fallback is not None:
        return fallback
    body = await request.body()
    logger.warning(
        "validation error: path=%s ctype=%s body=%r errors=%s",
        request.url.path,
        request.headers.get("content-type"),
        body[:200],
        exc.errors(),
    )
    return JSONResponse(
        {
            "detail": exc.errors(),
            "path": str(request.url.path),
            "ctype": request.headers.get("content-type"),
        },
        status_code=422,
    )


@app.get("/", include_in_schema=False)
def _root():
    return RedirectResponse("/ui/home", status_code=307)


@app.get("/healthz")
def healthz():
    return {"ok": True}
