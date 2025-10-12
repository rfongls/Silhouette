import json
import logging
import os
import sys
from pathlib import Path
import silhouette_core.compat.forwardref_shim  # noqa: F401  # ensure ForwardRef shim loads before FastAPI imports
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from starlette.responses import Response as StarletteResponse
from api.interop import router as interop_router
from api.interop_gen import router as interop_gen_router, try_generate_on_validation_error
from api.security import router as security_router
from api.ui import router as ui_router, templates as ui_templates
from api.ui_interop import router as ui_interop_router
from api.ui_settings import router as ui_settings_router
from api.ui_security import router as ui_security_router
from api.diag import router as diag_router
from api.http_logging import install_http_logging
from api.diag_fallback import ensure_diagnostics
from api.debug_log import log_debug_event
from api.metrics import router as metrics_router
from ui_home import router as ui_home_router
from ui_pages import router as ui_pages_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).resolve().parent
_HTTP_LOG_PATH = _BASE_DIR / "out" / "interop" / "server_http.log"
_STATIC_DIR = _BASE_DIR / "static"

app = FastAPI(
    debug=True,
    title="Silhouette Core Interop",
    openapi_url=None,
    docs_url=None,
    redoc_url=None,
)


def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.lower() not in {"", "0", "false", "off"}


_ENGINE_V2_ENABLED = _is_truthy(os.getenv("ENGINE_V2"))
app.state.engine_v2_enabled = _ENGINE_V2_ENABLED
ui_templates.env.globals["engine_v2_enabled"] = _ENGINE_V2_ENABLED

app.include_router(ui_home_router)
for r in (
    ui_router,
    ui_interop_router,
    ui_settings_router,
    ui_security_router,
    interop_gen_router,  # specific generator endpoint
    interop_router,      # generic tools (now under /api/interop/exec/{tool})
    security_router,
    metrics_router,
    diag_router,         # diagnostics
    ui_pages_router,
):
    app.include_router(r)
if _ENGINE_V2_ENABLED:
    from api.engine import router as engine_router
    from api.engine_jobs import router as engine_jobs_router
    from api.agent import router as agent_router
    from api.endpoints import router as endpoints_router
    from api.engine_assist import router as engine_assist_router
    from api.engine_messages import router as engine_messages_router
    from api.engine_pipelines import router as engine_pipelines_router
    from api.engine_profiles import router as engine_profiles_router
    from api.mllp_send import router as mllp_send_router
    from api.insights import router as insights_router
    from api.ui_engine import router as ui_engine_router

    for feature_router in (
        engine_router,
        engine_jobs_router,
        engine_profiles_router,
        engine_pipelines_router,
        engine_messages_router,
        agent_router,
        endpoints_router,
        mllp_send_router,
        engine_assist_router,
        insights_router,
        ui_engine_router,
    ):
        app.include_router(feature_router)
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
# Keep the registration near the bottom so it is easy to toggle during local
# investigations. The middleware ensures the log directory exists and degrades
# to console-only logging if file access fails.
install_http_logging(app, log_path=_HTTP_LOG_PATH)
ensure_diagnostics(app, http_log_path=_HTTP_LOG_PATH)


@app.get("/", include_in_schema=False)
async def _root_redirect():
    if app.state.engine_v2_enabled:
        return RedirectResponse(url="/ui/engine")
    return RedirectResponse(url="/ui")


# Lightweight health probe for startup checks and monitors
@app.get("/healthz", include_in_schema=False)
@app.head("/healthz", include_in_schema=False)
async def _healthz():
    return PlainTextResponse("ok", status_code=200)


@app.on_event("startup")
async def _bootstrap_insights_schema() -> None:
    """Ensure the Insights schema exists before serving requests."""
    try:
        from insights.store import get_store

        store = get_store()
        store.ensure_schema()
        db_url = os.getenv("INSIGHTS_DB_URL", "sqlite:///data/insights.db")
        logger.info("Insights DB ready: %s (ENGINE_V2=%s)", db_url, app.state.engine_v2_enabled)
    except Exception:
        logger.exception("Failed to ensure Insights schema on startup")
        raise

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
    # Do not consume resp.body_iterator here; http_logging middleware already
    # captures and replays bodies safely. Simply log the status and content type
    # to avoid draining streamed responses.
    print(
        "[TRACE] -> %s %s ctype=%s"
        % (
            resp.status_code,
            request.url.path,
            resp.headers.get("content-type"),
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
    logger.info("Silhouette starting: %d routes mounted, root_path=%r", len(app.routes), app.root_path)
    for sample in [
        "/api/diag/routes",
        "/api/diag/logs",
        "/ui/home/debug-log",
        "/api/interop/generate",
    ]:
        present = any(getattr(r, "path", "") == sample for r in app.routes)
        logger.info("CHECK route present? %s = %s", sample, present)
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

    try:
        log_debug_event("startup", message="server boot complete")
    except Exception as exc:
        logger.warning("could not prime generator_debug.log: %s", exc)


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


@app.exception_handler(HTTPException)
async def _http_exc_logger(request: Request, exc: HTTPException):
    logging.getLogger("silhouette.http").info(
        "HTTPException: %s %s -> %s detail=%r",
        request.method,
        request.url.path,
        exc.status_code,
        getattr(exc, "detail", None),
    )
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.exception_handler(Exception)
async def _log_unhandled_exception(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s", request.url)
    return PlainTextResponse("Internal Server Error", status_code=500)


@app.get("/", include_in_schema=False)
def _root():
    if getattr(app.state, "engine_v2_enabled", False):
        return RedirectResponse("/ui/landing", status_code=307)
    return RedirectResponse("/ui/home", status_code=307)


@app.get("/ping", include_in_schema=False)
def _ping() -> PlainTextResponse:
    """Lightweight health check used by local launch scripts."""
    return PlainTextResponse("ok", status_code=200)


@app.get("/healthz")
def healthz():
    return {"ok": True}
