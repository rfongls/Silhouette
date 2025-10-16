from __future__ import annotations

from html import escape
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from silhouette_core.interop.deid import apply_deid_with_template, deidentify_message
from silhouette_core.interop.validate_workbook import validate_message, validate_with_template

from api.interop_gen import (
    _build_logic_map,
    _build_success_rows,
    _count_issue_severities,
    _enrich_validate_issues,
    _extract_deid_targets_from_template,
    _maybe_load_deid_template,
    _maybe_load_validation_template,
    _normalize_validation_result,
    _normalize_index,
    _split_hl7_messages,
    _summarize_validation_for_table,
    _compute_deid_coverage,
    _deid_action_and_logic,
)


templates = Jinja2Templates(directory="templates")
router = APIRouter()


def _escape(value: str | None) -> str:
    return escape(value or "", quote=False)


def _maybe_text(*values: Optional[str]) -> str:
    for value in values:
        if value:
            text = str(value).strip()
            if text:
                return text
    return ""


def _status_from_counts(applied: int, total: int) -> str:
    if total <= 0:
        return "unknown"
    if applied >= total:
        return "pass"
    return "fail"


def _filter_rows(
    rows: Iterable[Dict[str, Any]],
    *,
    segment: str = "",
    action: str = "",
    parameter: str = "",
    status: str = "",
) -> List[Dict[str, Any]]:
    seg_filter = segment.strip().upper()
    action_filter = action.strip().lower()
    param_filter = parameter.strip().lower()
    status_filter = status.strip().lower()

    filtered: List[Dict[str, Any]] = []
    for row in rows:
        if seg_filter and row.get("segment", "").upper() != seg_filter:
            continue
        if action_filter and row.get("action", "").lower() != action_filter:
            continue
        if param_filter and param_filter not in row.get("parameter", "").lower():
            continue
        if status_filter:
            if row.get("status", "").lower() != status_filter:
                continue
        filtered.append(row)
    return filtered


def _render_deid_table(rows: Sequence[Dict[str, Any]], total_messages: int) -> str:
    if not rows:
        return (
            "<div class='muted small'>No processed rules matched the current filters. "
            "Run De-identify or clear the filters to see coverage.</div>"
        )

    header = (
        "<table class='small' style=\"width:100%;border-collapse:collapse\">"
        "<thead><tr>"
        "<th style='text-align:left;padding:0.5rem'>SEG</th>"
        "<th style='text-align:left;padding:0.5rem'>Field</th>"
        "<th style='text-align:left;padding:0.5rem'>Comp</th>"
        "<th style='text-align:left;padding:0.5rem'>Sub</th>"
        "<th style='text-align:left;padding:0.5rem'>Action</th>"
        "<th style='text-align:left;padding:0.5rem'>Logic</th>"
        "<th style='text-align:right;padding:0.5rem'>Applied</th>"
        "<th style='text-align:right;padding:0.5rem'>Total</th>"
        "<th style='text-align:right;padding:0.5rem'>%</th>"
        "</tr></thead><tbody>"
    )
    body_rows = []
    for row in rows:
        body_rows.append(
            "<tr>"
            f"<td style='padding:0.5rem'><code class='mono'>{_escape(row.get('segment')) or '—'}</code></td>"
            f"<td style='padding:0.5rem'><code class='mono'>{_escape(row.get('field_display')) or '—'}</code></td>"
            f"<td style='padding:0.5rem'><code class='mono'>{_escape(row.get('component_display')) or '—'}</code></td>"
            f"<td style='padding:0.5rem'><code class='mono'>{_escape(row.get('subcomponent_display')) or '—'}</code></td>"
            f"<td style='padding:0.5rem'>{_escape(row.get('action')) or '—'}</td>"
            f"<td style='padding:0.5rem'>{_escape(row.get('logic')) or '—'}</td>"
            f"<td style='padding:0.5rem;text-align:right'>{row.get('applied', 0)}</td>"
            f"<td style='padding:0.5rem;text-align:right'>{row.get('total', total_messages)}</td>"
            f"<td style='padding:0.5rem;text-align:right'>{row.get('pct', 0)}</td>"
            "</tr>"
        )
    footer = "</tbody></table>"
    return header + "".join(body_rows) + footer


def _build_deid_rows(
    before: str,
    after: str,
    template: Optional[dict],
    total_messages: int,
) -> List[Dict[str, Any]]:
    coverage_map, _ = _compute_deid_coverage(before, after)
    template_targets = _extract_deid_targets_from_template(template) if template else []

    logic_lookup = {
        (
            target.get("segment", "").upper(),
            _normalize_index(target.get("field")),
            _normalize_index(target.get("component")),
            _normalize_index(target.get("subcomponent")),
        ): (target.get("logic") or "—")
        for target in template_targets
        if isinstance(target, dict)
    }

    rule_index: Dict[Tuple[str, int, int, int], dict] = {}
    if isinstance(template, dict):
        for bucket in ("rules", "targets", "items"):
            entries = template.get(bucket)
            if not isinstance(entries, list):
                continue
            for rule in entries:
                if not isinstance(rule, dict):
                    continue
                seg = str(rule.get("segment") or rule.get("seg") or "").strip().upper()
                if not seg:
                    continue
                field_no = _normalize_index(rule.get("field") or rule.get("field_no") or rule.get("field_index"))
                if field_no <= 0:
                    continue
                comp_no = _normalize_index(rule.get("component") or rule.get("component_index"))
                sub_no = _normalize_index(rule.get("subcomponent") or rule.get("subcomponent_index"))
                rule_index[(seg, field_no, comp_no, sub_no)] = rule

    keyset = set(coverage_map.keys()) | set(logic_lookup.keys()) | set(rule_index.keys())
    rows: List[Dict[str, Any]] = []
    denominator = total_messages if total_messages else 1

    for seg, field_no, comp_no, sub_no in sorted(keyset):
        if not seg or field_no <= 0:
            continue
        applied = len(coverage_map.get((seg, field_no, comp_no, sub_no), set()))
        pct = round(100.0 * applied / denominator) if denominator else 0
        rule = rule_index.get((seg, field_no, comp_no, sub_no)) or {}
        action_label, rule_logic = _deid_action_and_logic(rule)
        logic_text = logic_lookup.get((seg, field_no, comp_no, sub_no)) or rule_logic or "—"
        parameter = str(rule.get("param") or rule.get("parameter") or "").strip()
        rows.append(
            {
                "segment": seg,
                "field": field_no,
                "component": comp_no or None,
                "subcomponent": sub_no or None,
                "action": action_label or "—",
                "logic": logic_text or "—",
                "parameter": parameter,
                "applied": applied,
                "total": total_messages,
                "pct": pct,
                "status": _status_from_counts(applied, denominator),
                "field_display": str(field_no) if field_no else "",
                "component_display": str(comp_no) if comp_no else "",
                "subcomponent_display": str(sub_no) if sub_no else "",
            }
        )
    return rows


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
    source_text = _maybe_text(text, message)
    template = _maybe_load_deid_template(deid_template)
    if template:
        try:
            after_text = apply_deid_with_template(source_text, template)
        except Exception:  # pragma: no cover - fallback to basic mode
            after_text = deidentify_message(source_text)
    else:
        after_text = deidentify_message(source_text)
    after_text = after_text or ""

    total_messages = max(len(_split_hl7_messages(after_text)) or len(_split_hl7_messages(source_text)), 1)
    rows = _build_deid_rows(source_text, after_text, template, total_messages)
    filtered_rows = _filter_rows(
        rows,
        segment=segment,
        action=action,
        parameter=parameter,
        status=status,
    )

    table_html = _render_deid_table(filtered_rows, total_messages)
    summary_html = (
        "<div class='muted micro' style=\"margin-bottom:0.5rem\">"
        f"Showing {len(filtered_rows)} rule{'s' if len(filtered_rows) != 1 else ''} (of {len(rows)} total)."
        "</div>"
    )
    body_html = f"<div data-deid-report>{summary_html}{table_html}</div>"
    fragment = (
        f"<pre id='deid-output' class='codepane limit10' hx-swap-oob='true'>{_escape(after_text)}</pre>"
        f"<div id='deid-report' class='codepane limit10'>{body_html}</div>"
    )
    return HTMLResponse(fragment)


def _filter_validate_rows(
    rows: Iterable[Dict[str, Any]],
    *,
    segment: str = "",
    rule: str = "",
    status: str = "",
) -> List[Dict[str, Any]]:
    seg_filter = segment.strip().upper()
    rule_filter = rule.strip().lower()
    status_filter = status.strip().lower()
    normalized_status = None
    if status_filter in {"pass", "passed"}:
        normalized_status = "passed"
    elif status_filter in {"fail", "failed", "error"}:
        normalized_status = "error"

    filtered: List[Dict[str, Any]] = []
    for row in rows:
        segment_value = str(row.get("segment") or "").upper()
        if seg_filter and segment_value != seg_filter:
            continue
        code_value = str(row.get("code") or row.get("rule") or "").lower()
        message_value = str(row.get("message") or "").lower()
        if rule_filter and rule_filter not in code_value and rule_filter not in message_value:
            continue
        severity = str(row.get("severity") or "error").lower()
        normalized = "passed" if severity in {"ok", "passed", "pass", "info"} else severity
        if normalized_status and normalized != normalized_status:
            continue
        filtered.append(row)
    return filtered


def _render_validate_table(rows: Sequence[Dict[str, Any]], total_messages: int) -> str:
    if not rows:
        return "<div class='muted small'>No validation results for the current filters.</div>"
    header = (
        "<table class='small' style=\"width:100%;border-collapse:collapse\">"
        "<thead><tr>"
        "<th style='text-align:left;padding:0.5rem'>Severity</th>"
        "<th style='text-align:left;padding:0.5rem'>Rule</th>"
        "<th style='text-align:left;padding:0.5rem'>SEG</th>"
        "<th style='text-align:left;padding:0.5rem'>Field</th>"
        "<th style='text-align:left;padding:0.5rem'>Comp</th>"
        "<th style='text-align:left;padding:0.5rem'>Sub</th>"
        "<th style='text-align:left;padding:0.5rem'>Message</th>"
        "<th style='text-align:right;padding:0.5rem'>Count</th>"
        "<th style='text-align:right;padding:0.5rem'>Total</th>"
        "<th style='text-align:right;padding:0.5rem'>%</th>"
        "</tr></thead><tbody>"
    )
    body_rows = []
    for row in rows:
        severity = str(row.get("severity") or "error").lower()
        severity_label = "Passed" if severity in {"ok", "passed", "pass", "info"} else ("Warning" if severity == "warning" else "Error")
        body_rows.append(
            "<tr>"
            f"<td style='padding:0.5rem'>{_escape(severity_label)}</td>"
            f"<td style='padding:0.5rem'><code class='mono'>{_escape(row.get('code') or row.get('rule') or '—')}</code></td>"
            f"<td style='padding:0.5rem'><code class='mono'>{_escape(row.get('segment') or '—')}</code></td>"
            f"<td style='padding:0.5rem'><code class='mono'>{_escape(str(row.get('field') or '—'))}</code></td>"
            f"<td style='padding:0.5rem'><code class='mono'>{_escape(str(row.get('component') or '—'))}</code></td>"
            f"<td style='padding:0.5rem'><code class='mono'>{_escape(str(row.get('subcomponent') or '—'))}</code></td>"
            f"<td style='padding:0.5rem'>{_escape(row.get('message') or '')}</td>"
            f"<td style='padding:0.5rem;text-align:right'>{row.get('count', 0)}</td>"
            f"<td style='padding:0.5rem;text-align:right'>{row.get('total', total_messages)}</td>"
            f"<td style='padding:0.5rem;text-align:right'>{row.get('pct', 0)}</td>"
            "</tr>"
        )
    footer = "</tbody></table>"
    return header + "".join(body_rows) + footer


@router.post("/ui/interop/validate", response_class=HTMLResponse, name="ui_validate")
def ui_validate(
    message: str = Form(""),
    text: str = Form(""),
    val_template: str | None = Form(None),
    segment: str = Form(""),
    rule: str = Form(""),
    status: str = Form(""),
) -> HTMLResponse:
    hl7_text = _maybe_text(message, text)
    template = _maybe_load_validation_template(val_template)
    if template:
        results = validate_with_template(hl7_text, template)
    else:
        results = validate_message(hl7_text)

    model = _normalize_validation_result(results, hl7_text)
    issues = _enrich_validate_issues(model.get("issues"), hl7_text)
    success_rows = _build_success_rows(template, issues, hl7_text)
    combined_rows = issues + success_rows
    counts = _count_issue_severities(combined_rows)

    total_messages = max(len(_split_hl7_messages(hl7_text)), 1)
    summary_rows, _segment_options = _summarize_validation_for_table(combined_rows, total_messages)

    filtered_rows = _filter_validate_rows(summary_rows, segment=segment, rule=rule, status=status)

    table_html = _render_validate_table(filtered_rows, total_messages)
    summary_html = (
        "<div class='muted micro' style=\"margin-bottom:0.5rem\">"
        f"Errors: {counts.get('errors', 0)} · Passed: {counts.get('ok', 0)} · Warnings: {counts.get('warnings', 0)}"
        "</div>"
    )
    body_html = f"<div data-validate-report>{summary_html}{table_html}</div>"
    validated_message = model.get("validated_message") or hl7_text
    fragment = (
        f"<pre id='validate-output' class='codepane limit10' hx-swap-oob='true'>{_escape(validated_message)}</pre>"
        f"<div id='validate-report' class='codepane limit10' data-val-root>{body_html}</div>"
    )
    return HTMLResponse(fragment)
