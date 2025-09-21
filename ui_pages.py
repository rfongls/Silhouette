"""Generic /ui/{page} router with safe template resolution."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from jinja2 import TemplateNotFound

from api.ui import install_link_for

router = APIRouter()
_templates = Jinja2Templates(directory="templates")
install_link_for(_templates)
_BASE = (Path("templates").resolve())


def _candidate_paths(page: str) -> list[str]:
    """Return relative template paths to probe for a given page slug."""
    normalized = page.strip().strip("/")
    if not normalized:
        return []
    # Collapse any ".." segments to avoid escaping the templates directory.
    segments = [seg for seg in normalized.split("/") if seg and seg not in {"..", "."}]
    if not segments:
        return []
    joined = "/".join(segments)
    return [
        f"{joined}.html",
        f"{joined}/index.html",
        f"ui/{joined}.html",
        f"ui/{joined}/index.html",
    ]


def _first_existing_template(page: str) -> str | None:
    for rel in _candidate_paths(page):
        candidate = (_BASE / rel).resolve()
        try:
            if not str(candidate).startswith(str(_BASE)):
                continue
        except Exception:
            continue
        if candidate.is_file():
            return rel
    return None


@router.get("/ui/{page:path}", response_class=HTMLResponse)
async def ui_page(page: str, request: Request) -> HTMLResponse:
    rel = _first_existing_template(page)
    if not rel:
        raise HTTPException(status_code=404, detail=f"UI template not found for '{page}'")
    try:
        return _templates.TemplateResponse(rel, {"request": request})
    except TemplateNotFound:
        raise HTTPException(status_code=404, detail=f"TemplateNotFound: {rel}")
