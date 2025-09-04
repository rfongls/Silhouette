from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from starlette.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/ui/security/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("security/dashboard.html", {"request": request})


@router.get("/ui/security/history", response_class=HTMLResponse)
async def history(request: Request):
    root = Path("out/security")
    files = sorted(root.glob("*/active/*.json"), reverse=True)
    items = [p.as_posix() for p in files]
    return templates.TemplateResponse("security/history.html", {"request": request, "items": items})


@router.get("/ui/security/history/view")
async def history_view(path: str):
    # Safely resolve path under ./out/
    base = Path("out").resolve()
    p = Path(path)
    try:
        target = p.resolve()
    except FileNotFoundError:
        raise HTTPException(404)
    if not target.is_file() or not str(target).startswith(str(base)):
        raise HTTPException(404)
    return PlainTextResponse(target.read_text(encoding="utf-8"), media_type="application/json")


def _load_env(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip()
    return data


@router.get("/ui/security/seeds", response_class=HTMLResponse)
async def seeds(request: Request):
    cve_path = Path("data/security/seeds/cve/cve_seed.json")
    kev_path = Path("data/security/seeds/kev/kev_seed.json")
    scope_path = Path("docs/cyber/scope_example.txt")
    context = {
        "request": request,
        "cve": cve_path.read_text(encoding="utf-8") if cve_path.exists() else "",
        "kev": kev_path.read_text(encoding="utf-8") if kev_path.exists() else "",
        "scope": scope_path.read_text(encoding="utf-8") if scope_path.exists() else "",
    }
    return templates.TemplateResponse("security/seeds.html", context)


@router.get("/ui/security/safety", response_class=HTMLResponse)
async def safety(request: Request):
    env = _load_env(Path("config/security.env"))
    return templates.TemplateResponse("security/safety.html", {"request": request, "env": env})
