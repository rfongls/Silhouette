from fastapi import FastAPI
from api.interop import router as interop_router
from api.ui import router as ui_router

app = FastAPI(title="Silhouette Core Interop")
app.include_router(interop_router)
app.include_router(ui_router)

@app.get("/healthz")
def healthz():
    return {"ok": True}
