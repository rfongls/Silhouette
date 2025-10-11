from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

from sqlalchemy import and_, func

from insights.store import InsightsStore
from insights.models import IssueRecord, MessageRecord, PipelineRecord, RunRecord


@dataclass
class AssistSuggestion:
    """Draft recommendations the UI can insert into YAML (commented)."""

    allowlist: List[Dict[str, Any]]
    severity_rules: List[Dict[str, Any]]
    notes: List[str]


@dataclass
class Anomaly:
    code: str
    segment: str | None
    count: int
    baseline: float
    deviation: float
    window_start: datetime
    window_end: datetime


def _recent_window(now: datetime, days: int) -> Tuple[datetime, datetime]:
    return now - timedelta(days=days), now


def _robust_z(x: float, median: float, mad: float, eps: float = 1e-6) -> float:
    return 0.6745 * (x - median) / (mad + eps)


def _require_pipeline(store: InsightsStore, pipeline_id: int) -> PipelineRecord:
    record = store.get_pipeline(pipeline_id)
    if record is None:
        raise ValueError(f"pipeline {pipeline_id} not found")
    return record


def _fetch_issue_counts(
    store: InsightsStore,
    pipeline_name: str,
    start: datetime,
    end: datetime,
) -> List[Tuple[str, str | None, int]]:
    with store.session() as session:
        query = (
            session.query(IssueRecord.code, IssueRecord.segment, func.count(IssueRecord.id))
            .join(MessageRecord, IssueRecord.message_id == MessageRecord.id)
            .join(RunRecord, MessageRecord.run_id == RunRecord.id)
            .filter(
                and_(
                    RunRecord.pipeline_name == pipeline_name,
                    RunRecord.created_at >= start,
                    RunRecord.created_at <= end,
                )
            )
            .group_by(IssueRecord.code, IssueRecord.segment)
        )
        return [(code, segment, count) for code, segment, count in query.all()]


def _fetch_recent_issue_rates(
    store: InsightsStore,
    pipeline_name: str,
    now: datetime,
    days_recent: int = 7,
    days_baseline: int = 30,
) -> Tuple[
    Dict[Tuple[str, str | None], float],
    Dict[Tuple[str, str | None], float],
    Tuple[datetime, datetime],
    Tuple[datetime, datetime],
]:
    start_recent, end_recent = _recent_window(now, days_recent)
    start_baseline, end_baseline = _recent_window(now, days_baseline)

    recent_counts = _fetch_issue_counts(store, pipeline_name, start_recent, end_recent)
    baseline_counts = _fetch_issue_counts(store, pipeline_name, start_baseline, end_baseline)

    denom_recent = max((end_recent - start_recent).days, 1)
    denom_baseline = max((end_baseline - start_baseline).days, 1)

    recent_rates = {(code, segment): count / denom_recent for code, segment, count in recent_counts}
    baseline_rates = {
        (code, segment): count / denom_baseline for code, segment, count in baseline_counts
    }
    return recent_rates, baseline_rates, (start_recent, end_recent), (start_baseline, end_baseline)


def compute_anomalies(
    store: InsightsStore,
    pipeline_id: int,
    now: datetime,
    recent_days: int = 7,
    baseline_days: int = 30,
    min_rate: float = 0.1,
) -> List[Anomaly]:
    pipeline = _require_pipeline(store, pipeline_id)
    recent_rates, baseline_rates, recent_window, _ = _fetch_recent_issue_rates(
        store, pipeline.name, now, recent_days, baseline_days
    )

    anomalies: List[Anomaly] = []
    for key, recent_rate in recent_rates.items():
        if recent_rate < min_rate:
            continue
        baseline_rate = baseline_rates.get(key, 0.0)
        median = baseline_rate
        mad = max(baseline_rate * 0.1, 0.01)
        deviation = _robust_z(recent_rate, median, mad)
        code, segment = key
        day_span = max((recent_window[1] - recent_window[0]).days, 1)
        anomalies.append(
            Anomaly(
                code=code,
                segment=segment,
                count=int(recent_rate * day_span),
                baseline=baseline_rate,
                deviation=deviation,
                window_start=recent_window[0],
                window_end=recent_window[1],
            )
        )

    anomalies.sort(key=lambda anomaly: abs(anomaly.deviation), reverse=True)
    return anomalies[:20]


def suggest_allowlist(
    store: InsightsStore,
    pipeline_id: int,
    now: datetime,
    lookback_days: int = 14,
    min_occurrences: int = 3,
) -> AssistSuggestion:
    pipeline = _require_pipeline(store, pipeline_id)
    start, end = _recent_window(now, lookback_days)
    counts: Counter[str] = Counter()
    segments: Dict[str, Counter[str]] = defaultdict(Counter)

    with store.session() as session:
        query = (
            session.query(IssueRecord.code, IssueRecord.segment)
            .join(MessageRecord, IssueRecord.message_id == MessageRecord.id)
            .join(RunRecord, MessageRecord.run_id == RunRecord.id)
            .filter(
                and_(
                    RunRecord.pipeline_name == pipeline.name,
                    RunRecord.created_at >= start,
                    RunRecord.created_at <= end,
                )
            )
        )
        for code, segment in query.all():
            counts[code] += 1
            if segment:
                segments[code][segment] += 1

    allowlist: List[Dict[str, Any]] = []
    severity_rules: List[Dict[str, Any]] = []
    notes: List[str] = []

    for code, occurrences in counts.most_common(15):
        if occurrences < min_occurrences:
            continue
        if "segment.missing" in code:
            most_common_segment = segments[code].most_common(1)
            if most_common_segment:
                selector, _ = most_common_segment[0]
                allowlist.append({"code": code, "selector": selector, "action": "ignore"})
                notes.append(
                    f"Frequent missing segment: {selector} for {code}, proposing ignore."
                )
                continue
        severity_rules.append({"code": code, "promote": "error->warning"})
        notes.append(f"High-frequency issue {code}: propose downgrade to warning.")

    return AssistSuggestion(allowlist=allowlist, severity_rules=severity_rules, notes=notes)


def render_draft_yaml(suggestion: AssistSuggestion) -> str:
    lines: List[str] = []
    lines.append("# --- BEGIN ML ASSIST SUGGESTIONS (Phase 4) ---")
    if suggestion.notes:
        lines.append("# notes:")
        for note in suggestion.notes:
            lines.append(f"#   - {note}")
    if suggestion.allowlist:
        lines.append("# allowlist:")
        for item in suggestion.allowlist:
            lines.append(f"#   - code: {item['code']}")
            if item.get("selector"):
                lines.append(f"#     selector: {item['selector']}")
            lines.append(f"#     action: {item['action']}")
    if suggestion.severity_rules:
        lines.append("# severity_rules:")
        for rule in suggestion.severity_rules:
            lines.append(f"#   - code: {rule['code']}")
            lines.append(f"#     promote: {rule['promote']}")
    lines.append("# --- END ML ASSIST SUGGESTIONS ---")
    return "\n".join(lines)
