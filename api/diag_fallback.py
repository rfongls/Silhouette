"""Helpers to guarantee diagnostics endpoints exist even if routers are omitted."""
from __future__ import annotations

import html
from pathlib import Path
from typing import Iterable

from fastapi import FastAPI
from starlette.responses import HTMLResponse, JSONResponse, Response as StarletteResponse

__all__ = ["ensure_diagnostics"]

_HTTP_LOG_DEFAULT = Path("out/interop/server_http.log")
_GENERATOR_LOG = Path("out/interop/generator_debug.log")


def _route_exists(app: FastAPI, path: str, methods: Iterable[str]) -> bool:
    wanted = {m.upper() for m in methods}
    for route in app.routes:
        if getattr(route, "path", None) != path:
            continue
        have = set(getattr(route, "methods", []) or [])
        if wanted.issubset(have):
            return True
    return False


def _tail_lines(path: Path, limit: int) -> list[str]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            lines = handle.readlines()[-limit:]
    except Exception:
        return []
    return [line.rstrip("\n") for line in lines]


def _combine_logs(limit: int, http_log_path: Path | None) -> list[str]:
    lines: list[str] = []
    if http_log_path is not None:
        lines.extend(_tail_lines(http_log_path, limit))
    lines.extend(_tail_lines(_GENERATOR_LOG, limit))
    return lines[-limit:]


def ensure_diagnostics(
    app: FastAPI,
    *,
    http_log_path: Path | str | None = _HTTP_LOG_DEFAULT,
) -> None:
    """Install fallback diagnostic routes if they are missing."""

    resolved_http_log = Path(http_log_path) if http_log_path is not None else None

    if resolved_http_log is not None:
        try:
            resolved_http_log.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            # Best effort; logging will still work if the directory exists later.
            pass

    if not _route_exists(app, "/api/diag/routes", ("GET",)):
        @app.get("/api/diag/routes", name="diag_list_routes")
        async def _diag_routes() -> JSONResponse:
            payload = []
            for route in app.routes:
                payload.append(
                    {
                        "path": getattr(route, "path", None),
                        "name": getattr(route, "name", None),
                        "methods": sorted(list(getattr(route, "methods", []) or [])),
                    }
                )
            return JSONResponse({"routes": payload})

    if not _route_exists(app, "/api/diag/logs", ("GET",)):
        @app.get("/api/diag/logs", name="diag_combined_logs")
        async def _diag_logs(limit: int = 200, format: str = "text"):
            limit = max(1, min(2000, int(limit or 200)))
            lines = _combine_logs(limit, resolved_http_log)
            fmt = (format or "text").lower()
            if fmt == "html":
                escaped = "\n".join(html.escape(line) for line in lines)
                body = f"<pre class='scrollbox' style='max-height:18rem'>{escaped}</pre>"
                return HTMLResponse(body)
            content = "\n".join(lines)
            if content:
                content += "\n"
            return StarletteResponse(content, media_type="text/plain")

    if not _route_exists(app, "/ui/home/debug-log", ("GET",)):
        @app.get("/ui/home/debug-log", name="ui_home_debug_log")
        async def _ui_home_debug_log(limit: int = 120, target: str | None = None):
            limit = max(1, min(2000, int(limit or 120)))
            lines = _combine_logs(limit, resolved_http_log)
            recent = lines[-5:]
            escaped = "\n".join(html.escape(line) for line in recent)
            html_body = ["<div class='stack gap-sm'>"]
            html_body.append(
                "<div class='muted micro'>Diagnostics fallback active — showing combined tail.</div>"
            )
            html_body.append(
                f"<pre class='scrollbox small' style='max-height:18rem'>{escaped}</pre>"
            )
            html_body.append("</div>")
            return HTMLResponse("".join(html_body))

    if not _route_exists(app, "/ui/home/debug-log", ("POST",)):
        @app.post("/ui/home/debug-log", name="ui_home_debug_log_update")
        async def _ui_home_debug_log_update(limit: int = 120):
            limit = max(1, min(2000, int(limit or 120)))
            lines = _combine_logs(limit, resolved_http_log)
            escaped = "\n".join(html.escape(line) for line in lines[-5:])
            body = f"<div class='stack gap-sm'><pre class='scrollbox small'>{escaped}</pre></div>"
            return HTMLResponse(body)

    if not any(
        getattr(route, "path", None) == "/ui/home" and "GET" in (getattr(route, "methods", []) or [])
        for route in app.routes
    ):
        # Provide a minimal fallback Reports home if the UI router was skipped.
        @app.get("/ui/home", name="ui_home_fallback")
        async def _ui_home_fallback():
            body = (
                "<section class='card'>"
                "<h2>Silhouette Diagnostics</h2>"
                "<p class='muted'>UI router missing — fallback diagnostics are active.</p>"
                "<p><a href='/ui/home/debug-log'>View debug log</a></p>"
                "</section>"
            )
            return HTMLResponse(body)
