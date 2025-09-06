from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from api.interop import router as interop_router
from api.interop_gen import router as interop_gen_router
from api.security import router as security_router
from api.ui import router as ui_router

app = FastAPI(title="Silhouette Core Interop")
app.include_router(interop_router)
app.include_router(interop_gen_router)
app.include_router(security_router)
app.include_router(ui_router)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/healthz")
def healthz():
    return {"ok": True}
