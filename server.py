import logging
import sys
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.responses import RedirectResponse
from api.interop import router as interop_router
from api.interop_gen import router as interop_gen_router, try_generate_on_validation_error
from api.security import router as security_router
from api.ui import router as ui_router
from api.ui_interop import router as ui_interop_router
from api.ui_security import router as ui_security_router
from api.diag import router as diag_router

logging.basicConfig(level=logging.INFO)

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

logger = logging.getLogger(__name__)

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
