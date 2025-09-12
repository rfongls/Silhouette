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
    interop_gen_router,  # static /api/interop/generate first
    interop_router,      # generic /api/interop/{tool} after
    security_router,
):
    app.include_router(r)
app.mount("/static", StaticFiles(directory="static"), name="static")

logger = logging.getLogger(__name__)


@app.on_event("startup")
async def _route_sanity_check():
    all_posts = []
    for idx, r in enumerate(app.routes):
        path = getattr(r, "path", None)
        methods = getattr(r, "methods", set()) or set()
        if not path or "POST" not in methods:
            continue
        ep = getattr(r, "endpoint", None)
        mod = getattr(ep, "__module__", "?")
        name = getattr(ep, "__name__", "?")
        if path.startswith("/api/interop"):
            all_posts.append((idx, path, mod, name))

    for idx, path, mod, name in all_posts:
        print(f"[ROUTE]#{idx} POST {path} -> {mod}.{name}", file=sys.stderr)

    gen_idx = next((i for i, p, _, _ in all_posts if p == "/api/interop/generate"), None)
    param_idxs = [i for i, p, _, _ in all_posts if p.startswith("/api/interop/") and "{" in p]

    if gen_idx is None:
        raise RuntimeError("Missing POST /api/interop/generate route.")
    if any(gen_idx > i for i in param_idxs):
        raise RuntimeError(
            "Static /api/interop/generate is registered AFTER a param route and will be shadowed. "
            "Include interop_gen_router before interop_router."
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
