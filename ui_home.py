"""Dedicated router for the /ui/home entry point.

This isolates the explicit Reports Home handler so it can be registered
before any generic /ui/{page} routes while still preserving the existing
fallback/diagnostic behaviour when the underlying template is missing.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from jinja2 import TemplateNotFound

from api.ui import install_link_for, _load_skills

router = APIRouter()
_templates = Jinja2Templates(directory="templates")
install_link_for(_templates)

# The existing UI home lives at ui/home_reports.html, but we keep the broader
# search list so future template moves continue to render without code changes.
_CANDIDATES = [
    "ui/home_reports.html",
    "home/index.html",
    "ui/home/index.html",
    "home.html",
    "ui/home.html",
    "index.html",
]


def _first_existing(candidates: list[str]) -> str | None:
    base = Path("templates")
    for rel in candidates:
        candidate = base / rel
        try:
            if candidate.is_file():
                return rel
        except OSError:
            # Ignore invalid paths; continue searching remaining candidates.
            continue
    return None


def _diagnostic_page(reason: str) -> str:
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>Home (diagnostic)</title>"
        "<style>body{font:14px system-ui;margin:24px;color:#111}"
        "code{background:#f6f8fa;padding:2px 4px;border-radius:4px}</style>"
        "</head><body>"
        "  <h1>Home route loaded (diagnostic)</h1>"
        "  <p>This fallback renders when the expected Jinja template could not be used.</p>"
        "  <h3>What to do</h3>"
        "  <ol>"
        "    <li>Create one of these files under <code>templates/</code>:"
        "      <ul>"
        "        <li><code>ui/home_reports.html</code></li>"
        "        <li><code>home/index.html</code></li>"
        "        <li><code>ui/home/index.html</code></li>"
        "        <li><code>home.html</code> or <code>ui/home.html</code></li>"
        "      </ul>"
        "    </li>"
        "    <li>Ensure your handler passes <code>&#123;'request': request&#125;</code> to <code>TemplateResponse</code>.</li>"
        "    <li>Ensure the app is mounted with <code>name=\"static\"</code> so <code>url_for('static', ...)</code> works.</li>"
        "  </ol>"
        f"  <p><strong>Reason:</strong> {reason}</p>"
        "  <p><a href=\"/interop\">Open Interoperability</a></p>"
        "</body></html>"
    )


@router.get("/ui/home", response_class=HTMLResponse)
async def ui_home(request: Request) -> HTMLResponse:
    target = _first_existing(_CANDIDATES)
    if not target:
        return HTMLResponse(_diagnostic_page("No matching template file found."), status_code=200)

    context = {"request": request, "skills": _load_skills()}
    try:
        return _templates.TemplateResponse(target, context)
    except TemplateNotFound as exc:
        return HTMLResponse(_diagnostic_page(f"TemplateNotFound: {exc}"), status_code=200)
    except Exception as exc:  # pragma: no cover - defensive guard
        reason = f"Render error: {type(exc).__name__}: {exc}"
        return HTMLResponse(_diagnostic_page(reason), status_code=200)
