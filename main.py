from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.security import router as security_router
from api.interop import router as interop_router
from api.ui_security import router as ui_security_router
from api.ui_interop import router as ui_interop_router
from api.admin import router as admin_router

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(security_router)
app.include_router(interop_router)
app.include_router(ui_security_router)
app.include_router(ui_interop_router)
app.include_router(admin_router)


@app.get("/")
async def root():
    return {"ok": True}
