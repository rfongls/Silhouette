from __future__ import annotations

import logging
from pathlib import Path

import silhouette_core.compat.forwardref_shim  # noqa: F401  # ensure ForwardRef shim is active before FastAPI imports
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse

from api.security import router as security_router
from api.interop import router as interop_router
from api.ui_security import router as ui_security_router
from api.ui_interop import router as ui_interop_router
from api.ui import router as ui_router
from api.interop_gen import router as interop_gen_router, try_generate_on_validation_error
from api.admin import router as admin_router
from api.diag import router as diag_router
from api.http_logging import install_http_logging
from api.diag_fallback import ensure_diagnostics
from api.debug_log import log_debug_event
from api.metrics import router as metrics_router
from ui_home import router as ui_home_router
from ui_pages import router as ui_pages_router


logger = logging.getLogger(__name__)
_BASE_DIR = Path(__file__).resolve().parent
_HTTP_LOG_PATH = _BASE_DIR / "out" / "interop" / "server_http.log"
_STATIC_DIR = _BASE_DIR / "static"

app = FastAPI(
    openapi_url=None,
    docs_url=None,
    redoc_url=None,
)

# --- BEGIN DIAG SHIM (remove after we verify) ---
# 1) Static mount MUST be named "static" for url_for('static', ...) to work
try:
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
except Exception:
    # If it's already mounted, this will raise; that's fine to ignore.
    pass


@app.get("/__routes", include_in_schema=False)
def __routes():
    """Return the live routing table for quick inspection."""

    items = []
    for route in app.router.routes:
        methods = sorted(list(getattr(route, "methods", []) or []))
        items.append(
            {
                "path": getattr(route, "path", str(route)),
                "name": getattr(route, "name", None),
                "methods": methods,
            }
        )
    return JSONResponse(items)


HOME_FALLBACK = """<!doctype html><html><head>
<meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>Silhouette — Home (fallback)</title>
<style>body{font:14px system-ui;margin:24px}code{background:#f6f8fa;padding:2px 4px;border-radius:4px}</style>
</head><body>
  <h1>Silhouette — Home</h1>
  <p>This is a temporary fallback served by <code>/ui/home</code>.</p>
  <p>If your real template exists, we'll switch to it after routing is confirmed.</p>
  <p><a href=\"/__routes\">List routes</a> · <a href=\"/docs\">OpenAPI</a></p>
</body></html>"""


@app.get("/ui/home", include_in_schema=False)
def __home_fallback(_: Request):
    return HTMLResponse(HOME_FALLBACK, status_code=200)


# --- END DIAG SHIM ---

# Register the explicit /ui/home route before any catch-all UI handlers.
app.include_router(ui_home_router)
for r in (
    ui_router,
    ui_interop_router,
    ui_security_router,
    interop_gen_router,  # specific generator endpoint
    interop_router,      # generic tools (now under /api/interop/exec/{tool})
    security_router,
    diag_router,
    admin_router,
    metrics_router,
    ui_pages_router,     # generic /ui/{page} catch-all (must come last)
):
    app.include_router(r)

# Keep the install close to the bottom so it can be commented out quickly when
# isolating failures. The middleware creates the log directory on demand and
# falls back to console logging if file access is unavailable.
# install_http_logging(app, log_path=_HTTP_LOG_PATH)
ensure_diagnostics(app, http_log_path=_HTTP_LOG_PATH)


@app.exception_handler(RequestValidationError)
async def _handle_validation(request: Request, exc: RequestValidationError):
    fallback = await try_generate_on_validation_error(request, exc)
    if fallback is not None:
        return fallback
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
    # Echo the stack trace to stderr so local runs immediately surface the root cause.
    import traceback
    import sys

    print(f"\n--- Unhandled exception on {request.url} ---", file=sys.stderr)
    traceback.print_exc()
    return PlainTextResponse("Internal Server Error", status_code=500)


@app.get("/", include_in_schema=False)
def _root():
    return RedirectResponse("/ui/home", status_code=307)


@app.on_event("startup")
async def _prime_debug_log():
    try:
        log_debug_event("startup", message="main app boot complete")
    except Exception as exc:
        logger.warning("could not prime generator_debug.log: %s", exc)
