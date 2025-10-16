from __future__ import annotations

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse
from silhouette_core.interop.deid import apply_deid_with_template, deidentify_message
from silhouette_core.interop.validate_workbook import validate_message, validate_with_template

router = APIRouter()


def _esc(value: str | None) -> str:
    return (value or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


@router.post("/ui/interop/deidentify", response_class=HTMLResponse, name="ui_deidentify")
def ui_deidentify(
    text: str = Form(""),
    message: str = Form(""),
    deid_template: str | None = Form(None),
    segment: str = Form(""),
    action: str = Form(""),
    parameter: str = Form(""),
    status: str = Form(""),
) -> HTMLResponse:
    source = text or message
    result = (
        apply_deid_with_template(source, deid_template)
        if deid_template
        else deidentify_message(source)
    )
    if isinstance(result, dict):
        output_text = result.get("text") or source
        rows = result.get("processed") or []
    else:
        output_text = result or source
        rows = []

    def _match(row: dict) -> bool:
        seg = (segment or "").strip().upper()
        act = (action or "").strip().lower()
        param = (parameter or "").strip().lower()
        stat = (status or "").strip().lower()
        if seg and (row.get("segment") or "").upper() != seg:
            return False
        if act and (row.get("action") or "").lower() != act:
            return False
        if param and param not in (row.get("parameter") or "").lower():
            return False
        if stat and (row.get("status") or "").lower() != stat:
            return False
        return True

    filtered = [row for row in rows if isinstance(row, dict) and _match(row)]
    if filtered:
        body = "".join(
            "<tr>"
            f"<td>{_esc(row.get('segment'))}</td>"
            f"<td>{_esc(row.get('action'))}</td>"
            f"<td>{_esc(row.get('parameter'))}</td>"
            f"<td>{_esc(row.get('status'))}</td>"
            "</tr>"
            for row in filtered
        )
    else:
        body = "<tr><td colspan='4' class='muted'>No items</td></tr>"

    fragment = (
        f"<pre id='deid-output' class='codepane limit10' hx-swap-oob='true'>{_esc(output_text)}</pre>"
        "<div id='deid-report'>"
        "<table class='small'>"
        "<thead><tr><th>SEG</th><th>Action</th><th>Parameter</th><th>Status</th></tr></thead>"
        f"<tbody>{body}</tbody>"
        "</table>"
        "</div>"
    )
    return HTMLResponse(fragment)


@router.post("/ui/interop/validate", response_class=HTMLResponse, name="ui_validate")
def ui_validate(
    message: str = Form(""),
    val_template: str | None = Form(None),
    segment: str = Form(""),
    rule: str = Form(""),
    status: str = Form(""),
) -> HTMLResponse:
    result = (
        validate_with_template(message, val_template)
        if val_template
        else validate_message(message)
    )
    ok = True
    results = []
    if isinstance(result, dict):
        ok = bool(result.get("ok", True))
        results = result.get("results") or []

    def _match(entry: dict) -> bool:
        seg = (segment or "").strip().upper()
        rule_filter = (rule or "").strip().lower()
        stat = (status or "").strip().lower()
        if seg and (entry.get("segment") or "").upper() != seg:
            return False
        if rule_filter and rule_filter not in (entry.get("rule") or "").lower():
            return False
        if stat and (entry.get("status") or "").lower() != stat:
            return False
        return True

    filtered = [entry for entry in results if isinstance(entry, dict) and _match(entry)]
    if filtered:
        items = "".join(
            "<li>"
            f"{_esc(entry.get('segment'))} · {_esc(entry.get('rule'))} · {_esc(entry.get('status'))}"
            "</li>"
            for entry in filtered
        )
    else:
        items = "<li class='muted'>No results</li>"

    badge = "PASS" if ok else "FAIL"
    fragment = (
        f"<pre id='validate-output' class='codepane limit10' hx-swap-oob='true'>{_esc(message)}</pre>"
        "<div id='validate-report'>"
        f"<div>Result: <span class='badge'>{badge}</span></div>"
        f"<ul class='mt'>{items}</ul>"
        "</div>"
    )
    return HTMLResponse(fragment)
