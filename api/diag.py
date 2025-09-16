from fastapi import APIRouter, Request, FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse
from api.debug_log import LOG_FILE, tail_debug_lines

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


@router.get("/api/diag/routes")
async def list_routes(request: Request):
    app: FastAPI = request.app
    out = []
    for r in app.routes:
        try:
            name = getattr(r, "name", None)
            path = getattr(r, "path", None)
            methods = list(getattr(r, "methods", []) or [])
            if path:
                out.append({"name": name, "path": path, "methods": methods})
        except Exception:
            pass
    out.sort(key=lambda x: (x["path"], ",".join(x["methods"])))
    return JSONResponse({"routes": out})

@router.get("/api/diag/logs")
async def get_debug_logs(limit: int = 200, format: str = "json"):
    lines = tail_debug_lines(limit)
    payload = {
        "lines": lines,
        "limit": limit,
        "path": str(LOG_FILE),
        "count": len(lines),
    }
    if format.lower() in {"text", "plain", "txt"}:
        text = "\n".join(lines)
        if text:
            text += "\n"
        return PlainTextResponse(text or "", media_type="text/plain")
    return JSONResponse(payload)
