"""Explicit /ui/home route with template discovery and diagnostics."""
from __future__ import annotations
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from jinja2 import TemplateNotFound
from api.ui import install_link_for, _load_skills

router = APIRouter()
_templates = Jinja2Templates(directory=str(Path("templates")))
install_link_for(_templates)

# Candidate template locations ordered by preference.
CANDIDATES = [
    "home/index.html",
    "ui/home/index.html",
    "home.html",
    "ui/home.html",
    "ui/home_reports.html",
    "index.html",
]


def _first_existing(path_list: list[str]) -> str | None:
    base = Path("templates")
    for rel in path_list:
        try:
            candidate = base / rel
        except TypeError:
            # Skip invalid entries defensively.
            continue
        if candidate.is_file():
            return rel
    return None


def _diagnostic_page(missing_reason: str) -> str:
    return f"""<!doctype html><html><head><meta charset=\"utf-8\">
<title>Silhouette — Home (diagnostic)</title>
<style>body{{font:14px system-ui;margin:24px;color:#111}}code{{background:#f6f8fa;padding:2px 4px;border-radius:4px}}</style>
</head><body>
  <h1>Home route loaded (diagnostic)</h1>
  <p>This fallback renders because the expected Jinja template could not be used.</p>
  <h3>Next steps</h3>
  <ol>
    <li>Create one of these files under <code>templates/</code> (first match wins):
      <ul>
        <li><code>home/index.html</code></li>
        <li><code>ui/home/index.html</code></li>
        <li><code>home.html</code> or <code>ui/home.html</code></li>
        <li><code>ui/home_reports.html</code></li>
      </ul>
    </li>
    <li>Ensure the handler passes <code>{{"request": request}}</code> to <code>TemplateResponse</code>.</li>
    <li>Verify the app mounts static files with <code>name=\"static\"</code>.</li>
  </ol>
  <p><strong>Reason:</strong> {missing_reason}</p>
  <p><a href=\"/interop\">Open Interoperability</a></p>
</body></html>"""


@router.get("/ui/home", response_class=HTMLResponse)
async def ui_home(request: Request) -> HTMLResponse:
    """Render the Home dashboard, providing diagnostics when the template fails."""

    target = _first_existing(CANDIDATES)
    context = {"request": request, "skills": _load_skills()}

    if not target:
        return HTMLResponse(_diagnostic_page("No matching template file found."), status_code=200)

    try:
        return _templates.TemplateResponse(target, context)
    except TemplateNotFound as exc:
        return HTMLResponse(_diagnostic_page(f"TemplateNotFound: {exc}"), status_code=200)
    except Exception as exc:  # pragma: no cover - unexpected render errors
        return HTMLResponse(
            _diagnostic_page(f"Render error: {type(exc).__name__}: {exc}"),
            status_code=200,
        )
