import logging
import sys
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

logging.basicConfig(level=logging.INFO)

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


@app.on_event("startup")
async def _route_sanity_check():
    # Dump routes and fail if duplicates exist for POST /api/interop/generate
    routes = []
    for r in app.routes:
        path = getattr(r, "path", None)
        methods = getattr(r, "methods", set())
        if path == "/api/interop/generate" and "POST" in methods:
            ep = getattr(r, "endpoint", None)
            routes.append(
                (path, methods, getattr(ep, "__module__", "?"), getattr(ep, "__name__", "?"))
            )
    print(
        f"[ROUTE-CHECK] POST /api/interop/generate count={len(routes)}",
        file=sys.stderr,
    )
    for path, methods, mod, name in routes:
        print(f"[ROUTE] {methods} {path} -> {mod}.{name}", file=sys.stderr)

    if len(routes) != 1:
        raise RuntimeError(
            "Duplicate or missing POST /api/interop/generate route — fix before continuing."
        )


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
