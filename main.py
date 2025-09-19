from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
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

logger = logging.getLogger(__name__)
_BASE_DIR = Path(__file__).resolve().parent
_HTTP_LOG_PATH = _BASE_DIR / "out" / "interop" / "server_http.log"

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
for r in (
    ui_router,
    ui_interop_router,
    ui_security_router,
    interop_gen_router,  # specific generator endpoint
    interop_router,      # generic tools (now under /api/interop/exec/{tool})
    security_router,
    diag_router,
    admin_router,
):
    app.include_router(r)

install_http_logging(app, log_path=_HTTP_LOG_PATH)
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


@app.get("/", include_in_schema=False)
def _root():
    return RedirectResponse("/ui/home", status_code=307)


@app.on_event("startup")
async def _prime_debug_log():
    try:
        log_debug_event("startup", message="main app boot complete")
    except Exception as exc:
        logger.warning("could not prime generator_debug.log: %s", exc)
