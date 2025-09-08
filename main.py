from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse

from api.security import router as security_router
from api.interop import router as interop_router
from api.ui_security import router as ui_security_router
from api.ui_interop import router as ui_interop_router
from api.ui import router as ui_router
from api.interop_gen import router as interop_gen_router
from api.admin import router as admin_router

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
for r in (
    ui_router,
    ui_interop_router,
    ui_security_router,
    interop_router,
    interop_gen_router,
    security_router,
    admin_router,
):
    app.include_router(r)


@app.get("/", include_in_schema=False)
def _root():
    return RedirectResponse("/ui/home", status_code=307)
