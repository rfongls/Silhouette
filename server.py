import logging
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.responses import RedirectResponse
from api.interop import router as interop_router
from api.interop_gen import router as interop_gen_router
from api.security import router as security_router
from api.ui import router as ui_router
from api.ui_interop import router as ui_interop_router
from api.ui_security import router as ui_security_router

app = FastAPI(title="Silhouette Core Interop")
for r in (
    ui_router,
    ui_interop_router,
    ui_security_router,
    interop_router,
    interop_gen_router,
    security_router,
):
    app.include_router(r)
app.mount("/static", StaticFiles(directory="static"), name="static")

logger = logging.getLogger(__name__)


@app.exception_handler(RequestValidationError)
async def _log_request_validation(request: Request, exc: RequestValidationError):
    body = await request.body()
    logger.warning(
        "validation error: path=%s ctype=%s body=%r errors=%s",
        request.url.path,
        request.headers.get("content-type"),
        body[:200],
        exc.errors(),
    )
    return JSONResponse({"detail": exc.errors()}, status_code=422)


@app.get("/", include_in_schema=False)
def _root():
    return RedirectResponse("/ui/home", status_code=307)


@app.get("/healthz")
def healthz():
    return {"ok": True}
