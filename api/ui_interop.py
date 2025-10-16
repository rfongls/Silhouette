from __future__ import annotations

import json
import html
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from starlette.templating import Jinja2Templates
from api.ui import install_link_for
from api.interop_gen import (
    generate_messages,
    parse_any_request,
    _normalize_validation_result,
    _compute_deid_coverage,
    _extract_deid_targets_from_template,
    _deid_action_and_logic,
    _build_logic_map,
    _normalize_index,
)
from silhouette_core.interop.deid import deidentify_message, apply_deid_with_template
from silhouette_core.interop.validate_workbook import validate_message, validate_with_template
from api.debug_log import (
    LOG_FILE,
    tail_debug_lines,
    is_debug_enabled,
    log_debug_event,
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")
install_link_for(templates)

DEID_DIR = Path("configs/interop/deid_templates")
VAL_DIR = Path("configs/interop/validate_templates")


def _ensure_dirs() -> None:
    DEID_DIR.mkdir(parents=True, exist_ok=True)
    VAL_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Standalone pipeline presets & helpers
# ---------------------------------------------------------------------------
PIPELINE_PRESETS: dict[str, dict[str, object]] = {
    "local-2575": {
        "label": "Local MLLP (127.0.0.1:2575)",
        "host": "127.0.0.1",
        "port": 2575,
        "timeout": 5,
        "fhir_endpoint": "http://127.0.0.1:8080/fhir",
        "post_fhir": False,
    },
    "docker-2575": {
        "label": "Docker MLLP (localhost:2575)",
        "host": "localhost",
        "port": 2575,
        "timeout": 5,
        "fhir_endpoint": "http://localhost:8080/fhir",
        "post_fhir": False,
    },
}


def _pipeline_defaults(preset_key: str | None) -> dict[str, object]:
    preset = PIPELINE_PRESETS.get((preset_key or "").strip()) or {}
    return {
        "host": preset.get("host", ""),
        "port": preset.get("port", ""),
        "timeout": preset.get("timeout", 5),
        "fhir_endpoint": preset.get("fhir_endpoint", ""),
        "post_fhir": bool(preset.get("post_fhir", False)),
    }


def list_deid_templates() -> list[str]:
    _ensure_dirs()
    return [p.stem for p in sorted(DEID_DIR.glob("*.json"))]


def list_validation_templates() -> list[str]:
    _ensure_dirs()
    return [p.stem for p in sorted(VAL_DIR.glob("*.json"))]


def load_deid_template(name: str) -> dict:
    _ensure_dirs()
    path = DEID_DIR / f"{name}.json"
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"De-identify template '{name}' not found")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - malformed template
        raise HTTPException(status_code=400, detail=f"Invalid template JSON: {exc}") from exc


def load_validation_template(name: str) -> dict:
    _ensure_dirs()
    path = VAL_DIR / f"{name}.json"
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"Validation template '{name}' not found")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - malformed template
        raise HTTPException(status_code=400, detail=f"Invalid template JSON: {exc}") from exc

def _template_lists() -> tuple[list[str], list[str]]:
    return list_deid_templates(), list_validation_templates()


def _maybe_load_deid_template(name: str | None) -> dict | None:
    if not name:
        return None
    normalized = str(name).strip()
    if not normalized or normalized.lower() in {"builtin", "legacy", "none"}:
        return None
    return load_deid_template(normalized)


def _maybe_load_validation_template(name: str | None) -> dict | None:
    if not name:
        return None
    normalized = str(name).strip()
    if not normalized or normalized.lower() in {"builtin", "legacy", "none"}:
        return None
    return load_validation_template(normalized)


def _escape_html(value: str | None) -> str:
    return html.escape(value or "", quote=False)


def _as_bool(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _build_deid_rows(
    before_text: str,
    after_text: str,
    template: dict | None,
    raw_changes: Any,
) -> tuple[list[dict[str, Any]], int]:
    coverage_map, total_messages = _compute_deid_coverage(before_text, after_text)
    template_targets = _extract_deid_targets_from_template(template)
    logic_lookup: dict[tuple[str, int, int, int], str] = {
        (
            target.get("segment", ""),
            int(target.get("field") or 0),
            int(target.get("component") or 0),
            int(target.get("subcomponent") or 0),
        ): target.get("logic") or "—"
        for target in template_targets
        if target.get("segment") and int(target.get("field") or 0) > 0
    }

    rule_index: dict[tuple[str, int, int, int], dict[str, Any]] = {}
    if isinstance(template, dict):
        for bucket in ("rules", "targets", "items"):
            maybe_rules = template.get(bucket)
            if not isinstance(maybe_rules, list):
                continue
            for rule in maybe_rules:
                if not isinstance(rule, dict):
                    continue
                seg = str(rule.get("segment") or rule.get("seg") or "").strip().upper()
                if not seg:
                    continue
                field_no = _normalize_index(
                    rule.get("field") or rule.get("field_no") or rule.get("field_index")
                )
                if field_no <= 0:
                    continue
                comp_no = _normalize_index(
                    rule.get("component") or rule.get("component_index")
                )
                sub_no = _normalize_index(
                    rule.get("subcomponent") or rule.get("subcomponent_index")
                )
                rule_index[(seg, field_no, comp_no or 0, sub_no or 0)] = rule

    logic_map = _build_logic_map(raw_changes)
    for key, value in logic_map.items():
        if value and key not in logic_lookup:
            logic_lookup[key] = value

    rows: list[dict[str, Any]] = []
    keyset: set[tuple[str, int, int, int]] = set(coverage_map.keys())
    keyset.update(logic_lookup.keys())
    keyset.update(rule_index.keys())

    for seg, field_no, comp_no, sub_no in sorted(
        keyset, key=lambda item: (item[0], item[1], item[2], item[3])
    ):
        if not seg or field_no <= 0:
            continue
        applied = len(coverage_map.get((seg, field_no, comp_no, sub_no), set()))
        action_label, rule_logic = _deid_action_and_logic(
            rule_index.get((seg, field_no, comp_no or 0, sub_no or 0))
        )
        logic_text = logic_lookup.get((seg, field_no, comp_no, sub_no)) or rule_logic or "—"
        rows.append(
            {
                "segment": seg,
                "field": field_no,
                "component": comp_no or None,
                "subcomponent": sub_no or None,
                "action": action_label or "—",
                "logic": logic_text or "—",
                "applied": applied,
                "total": total_messages,
            }
        )

    return rows, total_messages


def _filter_deid_rows(
    rows: list[dict[str, Any]],
    segment_filter: str,
    action_filter: str,
    parameter_filter: str,
    status_filter: str,
) -> list[dict[str, Any]]:
    seg_text = (segment_filter or "").strip().upper()
    seg_match: str | None = None
    field_match: str | None = None
    if seg_text:
        if "-" in seg_text:
            seg_part, field_part = seg_text.split("-", 1)
            seg_match = seg_part.strip() or None
            field_match = field_part.strip() or None
        else:
            seg_match = seg_text

    act_text = (action_filter or "").strip().lower()
    param_text = (parameter_filter or "").strip().lower()
    status_text = (status_filter or "").strip().lower()

    filtered: list[dict[str, Any]] = []
    for row in rows:
        seg = (row.get("segment") or "").upper()
        field = str(row.get("field") or "")
        action = (row.get("action") or "").strip().lower()
        logic_text = (row.get("logic") or "").strip().lower()
        total = row.get("total") or 0
        applied = row.get("applied") or 0
        status = "pass" if total and applied >= total else "fail"

        if seg_match and seg != seg_match:
            continue
        if field_match and field_match and field != field_match:
            continue
        if act_text and action != act_text:
            continue
        if param_text and param_text not in logic_text:
            continue
        if status_text == "pass" and status != "pass":
            continue
        if status_text == "fail" and status != "fail":
            continue

        filtered.append({**row, "status": status})

    return filtered


def _render_deid_report(rows: list[dict[str, Any]], total_messages: int) -> str:
    if not rows:
        return "<p class='muted small'>No processed rules matched the current filters.</p>"

    header_parts = [
        "<table class='small' style=\"width:100%;border-collapse:collapse;font-size:0.9rem\">",
        "<thead><tr>",
        "<th style='text-align:left;padding:.4rem'>Segment</th>",
        "<th style='text-align:left;padding:.4rem'>Field</th>",
        "<th style='text-align:left;padding:.4rem'>Comp</th>",
        "<th style='text-align:left;padding:.4rem'>Subcomp</th>",
        "<th style='text-align:left;padding:.4rem'>Action</th>",
        "<th style='text-align:left;padding:.4rem'>Logic / Parameter</th>",
        "<th style='text-align:left;padding:.4rem'>Applied</th>",
        "<th style='text-align:left;padding:.4rem'>Status</th>",
        "</tr></thead><tbody>",
    ]
    header = "".join(header_parts)

    body_parts: list[str] = []
    for row in rows:
        status = row.get("status", "fail")
        chip = "<span class='chip'>PASS</span>" if status == "pass" else "<span class='chip'>FAIL</span>"
        body_parts.append(
            "<tr style='border-bottom:1px solid var(--color-border,#2b2f3a)'>"
            f"<td style='padding:.4rem'><code class='mono'>{_escape_html(str(row.get('segment') or '—'))}</code></td>"
            f"<td style='padding:.4rem'><code class='mono'>{_escape_html(str(row.get('field') or '—'))}</code></td>"
            f"<td style='padding:.4rem'><code class='mono'>{_escape_html(str(row.get('component') or '—'))}</code></td>"
            f"<td style='padding:.4rem'><code class='mono'>{_escape_html(str(row.get('subcomponent') or '—'))}</code></td>"
            f"<td style='padding:.4rem'>{_escape_html(str(row.get('action') or '—'))}</td>"
            f"<td style='padding:.4rem'>{_escape_html(str(row.get('logic') or '—'))}</td>"
            f"<td style='padding:.4rem'>{row.get('applied', 0)}/{total_messages}</td>"
            f"<td style='padding:.4rem'>{chip}</td>"
            "</tr>"
        )

    table = header + "".join(body_parts) + "</tbody></table>"
    return table


def _render_validate_report(rows: list[dict[str, Any]], ok: bool) -> str:
    if not rows:
        status = "<span class='chip'>PASS</span>" if ok else "<span class='chip'>FAIL</span>"
        return (
            f"<div class='muted small'>Validation {status} with no reported issues.</div>"
        )

    parts = [
        "<div class='muted small'>Issues returned by the validator.</div>",
        "<ul class='mt' style='line-height:1.4'>",
    ]
    for row in rows:
        status = row.get("status", "fail")
        badge = "<span class='chip'>PASS</span>" if status == "pass" else "<span class='chip'>FAIL</span>"
        segment = _escape_html(row.get("segment") or row.get("location") or "—")
        rule = _escape_html(row.get("rule") or row.get("code") or "—")
        message = _escape_html(row.get("message") or "—")
        parts.append(
            "<li style='margin-bottom:.35rem'>"
            f"<code class='mono'>{segment}</code> · {rule}<br />"
            f"<span class='muted'>{message}</span> {badge}"
            "</li>"
        )
    parts.append("</ul>")
    return "".join(parts)


def _safe_url_for(request: Request, name: str, fallback: str) -> str:
    try:
        return str(request.url_for(name))
    except Exception:
        return fallback

def _ui_urls(request: Request) -> dict[str, str]:
    """
    Provide all URLs the templates need, with hardcoded fallbacks so the UI
    keeps working even if a route name changes.
    """
    return {
        # UI form posts (HTML fallback):
        "ui_generate":   _safe_url_for(request, "ui_generate",   "/ui/interop/generate"),
        "ui_deidentify": _safe_url_for(request, "ui_deidentify", "/ui/interop/deidentify"),
        "ui_validate":   _safe_url_for(request, "ui_validate",   "/ui/interop/validate"),
        "ui_pipeline":   _safe_url_for(request, "ui_interop_pipeline", "/ui/interop/pipeline"),
        # API endpoints (HTMX fast path):
        "api_generate":  _safe_url_for(request, "generate_messages_endpoint", "/api/interop/generate"),
        "api_deidentify": _safe_url_for(request, "api_deidentify", "/api/interop/deidentify"),
        "api_deidentify_summary": _safe_url_for(
            request,
            "api_deidentify_summary",
            "/api/interop/deidentify/summary",
        ),
        "api_validate": _safe_url_for(request, "api_validate", "/api/interop/validate"),
        "api_validate_view": _safe_url_for(request, "interop_validate_view", "/api/interop/validate/view"),
        "api_pipeline_run": _safe_url_for(request, "run_pipeline", "/api/interop/pipeline/run"),
    }

@router.get("/ui/interop/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    deid, val = _template_lists()
    return templates.TemplateResponse(
        "ui/interop/skills.html",
        {"request": request, "urls": _ui_urls(request), "deid_templates": deid, "val_templates": val},
    )


@router.get("/ui/interop/skills", response_class=HTMLResponse)
async def interop_skills(request: Request):
    deid, val = _template_lists()
    return templates.TemplateResponse(
        "ui/interop/skills.html",
        {"request": request, "urls": _ui_urls(request), "deid_templates": deid, "val_templates": val},
    )


@router.get("/ui/interop/pipeline", response_class=HTMLResponse, name="ui_interop_pipeline")
async def interop_pipeline(request: Request, preset: str | None = None):
    """Modern standalone pipeline experience with generate/deid/validate/transport panels."""
    deid_templates, val_templates = _template_lists()
    defaults = _pipeline_defaults(preset)
    ctx = {
        "request": request,
        "deid_templates": deid_templates,
        "val_templates": val_templates,
        "urls": _ui_urls(request),
        "presets": PIPELINE_PRESETS,
        "preset_key": preset or "",
        "defaults": defaults,
        "log_path": str(LOG_FILE),
        "limit": 200,
        "refreshed": "",
        "rows": [],
    }
    return templates.TemplateResponse("ui/interop/pipeline.html", ctx)


@router.get("/ui/interop/history", response_class=HTMLResponse)
async def history(request: Request):
    root = Path("out/interop")
    files = sorted(root.glob("*/active/*.json"), reverse=True)
    items = [p.as_posix() for p in files]
    return templates.TemplateResponse("interop/history.html", {"request": request, "items": items, "urls": _ui_urls(request)})

@router.get("/ui/interop/logs/content", response_class=HTMLResponse)
async def interop_logs_content(request: Request, limit: int = 200):
    lines = tail_debug_lines(limit)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    ctx = {
        "request": request,
        "lines": lines,
        "limit": limit,
        "log_path": str(LOG_FILE),
        "enabled": is_debug_enabled(),
        "refreshed": ts,
    }
    return templates.TemplateResponse("ui/interop/_debug_log_content.html", ctx)


@router.get("/ui/interop/history/view")
async def history_view(path: str):
    base = Path("out").resolve()
    p = Path(path)
    try:
        target = p.resolve()
    except FileNotFoundError:
        raise HTTPException(404)
    if not target.is_file() or not str(target).startswith(str(base)):
        raise HTTPException(404)
    return PlainTextResponse(target.read_text(encoding="utf-8"), media_type="application/json")


# Pure-HTML fallback: when JS is disabled, the form posts here and we render a page.
@router.post("/ui/interop/generate", response_class=HTMLResponse)
async def ui_generate(request: Request):
    log_debug_event(
        "ui.generate.invoke",
        method=request.method,
        path=request.url.path,
        query=request.url.query,
        hx=request.headers.get("hx-request"),
        accept=request.headers.get("accept"),
        referer=request.headers.get("referer"),
        content_type=request.headers.get("content-type"),
    )
    body = await parse_any_request(request)
    log_debug_event(
        "ui.generate.body",
        keys=";".join(sorted(body.keys())),
        trigger=body.get("trigger"),
        template=body.get("template_relpath"),
        count=body.get("count"),
    )
    try:
        resp = generate_messages(body)
    except HTTPException as exc:
        log_debug_event(
            "ui.generate.error",
            status=exc.status_code,
            detail=getattr(exc, "detail", ""),
        )
        raise
    text = resp.body.decode("utf-8") if hasattr(resp, "body") else str(resp)
    accept = (request.headers.get("accept") or "").lower()
    hx = (request.headers.get("hx-request") or "").lower() == "true"
    log_debug_event(
        "ui.generate.result",
        hx=hx,
        accept=accept,
        bytes=len(text.encode("utf-8", errors="ignore")),
    )
    if hx or "text/plain" in accept:
        return PlainTextResponse(text, media_type="text/plain")
    return templates.TemplateResponse(
        "ui/interop/generate_result.html",
        {"request": request, "hl7_text": text}
    )

# De-identify (HTML fragment suitable for hx-swap)
@router.post("/ui/interop/deidentify", response_class=HTMLResponse)
async def ui_deidentify(request: Request):
    body = await parse_any_request(request)
    text = (body.get("text") or body.get("message") or "").strip()
    seed = body.get("seed")
    try:
        seed_int = int(seed) if seed not in (None, "") else None
    except Exception:
        seed_int = None

    if not text:
        empty_output = (
            "<pre id='deid-output' class='codepane limit10' hx-swap-oob='outerHTML'></pre>"
        )
        return HTMLResponse(
            empty_output
            + "<p class='muted small'>Provide an HL7 message to generate a processed-errors report.</p>"
        )

    tpl = _maybe_load_deid_template(body.get("deid_template") or body.get("template"))
    baseline_flag = _as_bool(body.get("apply_baseline"))

    if tpl or baseline_flag:
        tpl_payload = tpl or {"rules": []}
        result = apply_deid_with_template(text, tpl_payload, apply_baseline=baseline_flag)
    else:
        result = deidentify_message(text, seed=seed_int)

    raw_changes: Any = []
    if isinstance(result, dict):
        out_text = str(result.get("text") or "")
        raw_changes = result.get("changes") or []
    else:
        out_text = str(result or "")

    rows, total_messages = _build_deid_rows(text, out_text, tpl, raw_changes)
    filtered_rows = _filter_deid_rows(
        rows,
        body.get("segment", ""),
        body.get("action", ""),
        body.get("parameter", ""),
        body.get("status", ""),
    )
    report_html = _render_deid_report(filtered_rows, total_messages)

    output_html = (
        "<pre id='deid-output' class='codepane limit10' hx-swap-oob='outerHTML'>"
        f"{_escape_html(out_text)}</pre>"
    )

    return HTMLResponse(output_html + report_html)

# Validate (HTML fragment suitable for hx-swap)
@router.post("/ui/interop/validate", response_class=HTMLResponse)
async def ui_validate(request: Request):
    body = await parse_any_request(request)
    message = (body.get("message") or body.get("text") or "").strip()
    profile = body.get("profile")

    if not message:
        empty_output = (
            "<pre id='validate-output' class='codepane limit10' hx-swap-oob='outerHTML'></pre>"
        )
        return HTMLResponse(
            empty_output
            + "<p class='muted small'>Provide an HL7 message to run validation.</p>"
        )

    tpl = _maybe_load_validation_template(body.get("val_template") or body.get("template"))
    if tpl:
        res = validate_with_template(message, tpl)
    else:
        res = validate_message(message, profile=profile)

    normalized = _normalize_validation_result(res, message)
    validated_message = normalized.get("validated_message") or message
    issues = normalized.get("issues", []) or []
    counts = normalized.get("counts") or {}
    ok = bool(counts.get("errors") in (0, "0", None))

    segment_filter = (body.get("segment") or "").strip().upper()
    rule_filter = (body.get("rule") or "").strip().lower()
    status_filter = (body.get("status") or "").strip().lower()

    filtered: list[dict[str, Any]] = []
    for entry in issues:
        segment = (entry.get("segment") or entry.get("location") or "").strip()
        rule = (entry.get("code") or entry.get("rule") or "").strip()
        severity = (entry.get("severity") or "").strip().lower()
        status = "fail" if severity == "error" else "pass"
        if segment_filter and segment.upper() != segment_filter:
            continue
        if rule_filter and rule.lower() != rule_filter:
            continue
        if status_filter == "pass" and status != "pass":
            continue
        if status_filter == "fail" and status != "fail":
            continue
        filtered.append(
            {
                "segment": segment,
                "location": entry.get("location"),
                "rule": rule,
                "code": entry.get("code"),
                "message": entry.get("message") or entry.get("detail"),
                "status": status,
            }
        )

    report_html = _render_validate_report(filtered, ok)
    output_html = (
        "<pre id='validate-output' class='codepane limit10' hx-swap-oob='outerHTML'>"
        f"{_escape_html(validated_message)}</pre>"
    )
    return HTMLResponse(output_html + report_html)

