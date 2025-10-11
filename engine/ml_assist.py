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


@dataclass
class WindowStats:
    """Aggregate counts and per-day rates for a (code, segment) window."""

    counts: Dict[Tuple[str, str | None], int]
    rates: Dict[Tuple[str, str | None], float]
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
) -> Dict[Tuple[str, str | None], int]:
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
        return {
            (code, segment): count
            for code, segment, count in query.all()
        }


def _issue_stats_for_window(
    store: InsightsStore,
    pipeline_name: str,
    start: datetime,
    end: datetime,
) -> WindowStats:
    counts = _fetch_issue_counts(store, pipeline_name, start, end)
    denom = max((end - start).days, 1)
    rates = {key: count / denom for key, count in counts.items()}
    return WindowStats(counts=counts, rates=rates, window_start=start, window_end=end)


def compute_anomalies(
    store: InsightsStore,
    pipeline_id: int,
    now: datetime,
    recent_days: int = 7,
    baseline_days: int = 30,
    min_rate: float = 0.1,
) -> List[Anomaly]:
    pipeline = _require_pipeline(store, pipeline_id)
    recent_window = _issue_stats_for_window(
        store,
        pipeline.name,
        *_recent_window(now, recent_days),
    )
    baseline_window = _issue_stats_for_window(
        store,
        pipeline.name,
        *_recent_window(now, baseline_days),
    )

    anomalies: List[Anomaly] = []
    for key, recent_rate in recent_window.rates.items():
        if recent_rate < min_rate:
            continue
        baseline_rate = baseline_window.rates.get(key, 0.0)
        median = baseline_rate
        mad = max(baseline_rate * 0.1, 0.01)
        deviation = _robust_z(recent_rate, median, mad)
        code, segment = key
        day_span = max((recent_window.window_end - recent_window.window_start).days, 1)
        count = recent_window.counts.get(key, 0)
        anomalies.append(
            Anomaly(
                code=code,
                segment=segment,
                count=count if count else int(recent_rate * day_span),
                baseline=baseline_rate,
                deviation=deviation,
                window_start=recent_window.window_start,
                window_end=recent_window.window_end,
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
