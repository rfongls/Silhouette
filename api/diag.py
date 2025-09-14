from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()

@router.post("/api/diag/echo")
async def echo(request: Request):
    raw = await request.body()
    try:
        parsed_json = await request.json()
    except Exception:
        parsed_json = None
    form_data = None
    try:
        f = await request.form()
        form_data = {k: f.get(k) for k in f}
    except Exception:
        pass
    return JSONResponse({
        "method": request.method,
        "path": request.url.path,
        "content_type": request.headers.get("content-type"),
        "accept": request.headers.get("accept"),
        "hx": request.headers.get("hx-request"),
        "raw_len": len(raw or b""),
        "json": parsed_json,
        "form": form_data,
        "query": dict(request.query_params),
    })
