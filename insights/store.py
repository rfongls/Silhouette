"""High-level helpers for interacting with the insights database."""

from __future__ import annotations

import base64
import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator

from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from engine.contracts import Issue, Result
from api.sql_logging import install_sql_logging

from .models import Base, IssueRecord, MessageRecord, PipelineRecord, RunRecord

_DEFAULT_DB = Path("data") / "insights.db"


@dataclass
class InsightsStore:
    """Wrapper around SQLAlchemy sessions with convenience helpers."""

    url: str
    engine: Engine
    session_factory: sessionmaker

    @classmethod
    def from_env(cls, url: str | None = None) -> "InsightsStore":
        resolved = url or os.getenv("INSIGHTS_DB_URL")
        if not resolved:
            _DEFAULT_DB.parent.mkdir(parents=True, exist_ok=True)
            resolved = f"sqlite:///{_DEFAULT_DB}"  # relative path -> project data dir
        connect_args: Dict[str, Any] = {}
        if resolved.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        engine = create_engine(resolved, future=True, connect_args=connect_args)
        install_sql_logging(engine)
        try:
            Base.metadata.create_all(engine)
        except Exception:
            # In production we rely on Alembic migrations; during local dev/tests this
            # provides a convenient fallback without failing startup if migrations
            # haven't run yet.
            pass
        SessionFactory = sessionmaker(bind=engine, future=True, expire_on_commit=False)
        return cls(url=resolved, engine=engine, session_factory=SessionFactory)

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # --- Persistence helpers -------------------------------------------------

    def start_run(self, pipeline_name: str) -> RunRecord:
        with self.session() as session:
            run = RunRecord(pipeline_name=pipeline_name)
            session.add(run)
            session.flush()
            session.refresh(run)
            return run

    def record_result(self, *, run_id: int, result: Result) -> MessageRecord:
        with self.session() as session:
            message = MessageRecord(
                run_id=run_id,
                message_id=result.message.id,
                payload=_encode_payload(result.message.raw),
                meta=dict(result.message.meta or {}),
            )
            session.add(message)
            session.flush()
            for issue in result.issues:
                session.add(_issue_to_record(message.id, issue))
            session.flush()
            session.refresh(message)
            return message

    # --- Query helpers -------------------------------------------------------

    def summaries(self) -> dict[str, Any]:
        """Return aggregated counts for UI consumption."""

        with self.session() as session:
            run_rows = session.execute(
                select(RunRecord).order_by(RunRecord.created_at.desc())
            ).scalars().all()

            totals = {
                "runs": len(run_rows),
                "messages": session.execute(select(func.count(MessageRecord.id))).scalar_one(),
                "issues": session.execute(select(func.count(IssueRecord.id))).scalar_one(),
            }

            by_run = []
            for run in run_rows:
                message_count = session.execute(
                    select(func.count(MessageRecord.id)).where(MessageRecord.run_id == run.id)
                ).scalar_one()
                severity_counts = session.execute(
                    select(IssueRecord.severity, func.count(IssueRecord.id))
                    .join(MessageRecord)
                    .where(MessageRecord.run_id == run.id)
                    .group_by(IssueRecord.severity)
                ).all()
                issues = {sev: count for sev, count in severity_counts}
                by_run.append(
                    {
                        "run_id": run.id,
                        "pipeline": run.pipeline_name,
                        "messages": message_count,
                        "issues": {
                            "error": issues.get("error", 0),
                            "warning": issues.get("warning", 0),
                            "passed": issues.get("passed", 0),
                        },
                        "started_at": run.created_at.isoformat(),
                    }
                )

            by_rule = session.execute(
                select(IssueRecord.code, IssueRecord.severity, func.count(IssueRecord.id))
                .group_by(IssueRecord.code, IssueRecord.severity)
                .order_by(func.count(IssueRecord.id).desc())
            ).all()
            rules = [
                {"code": code, "severity": severity, "count": count}
                for code, severity, count in by_rule
            ]

            return {"totals": totals, "by_run": by_run, "by_rule": rules}

    # --- Pipeline CRUD helpers ---------------------------------------------

    def save_pipeline(
        self,
        *,
        name: str,
        yaml: str,
        spec: dict[str, Any],
        description: str | None = None,
        pipeline_id: int | None = None,
    ) -> PipelineRecord:
        with self.session() as session:
            if pipeline_id is not None:
                record = session.get(PipelineRecord, pipeline_id)
                if record is None:
                    raise KeyError(f"pipeline {pipeline_id} not found")
                record.name = name
                record.description = description
                record.yaml = yaml
                record.spec = spec
                session.add(record)
                session.flush()
                session.refresh(record)
                return record

            record = PipelineRecord(
                name=name,
                description=description,
                yaml=yaml,
                spec=spec,
            )
            session.add(record)
            session.flush()
            session.refresh(record)
            return record

    def list_pipelines(self) -> list[PipelineRecord]:
        with self.session() as session:
            return (
                session.query(PipelineRecord)
                .order_by(PipelineRecord.updated_at.desc())
                .all()
            )

    def get_pipeline(self, pipeline_id: int) -> PipelineRecord | None:
        with self.session() as session:
            return session.get(PipelineRecord, pipeline_id)

    def delete_pipeline(self, pipeline_id: int) -> bool:
        with self.session() as session:
            record = session.get(PipelineRecord, pipeline_id)
            if record is None:
                return False
            session.delete(record)
            return True

    def persist_run_results(
        self, *, pipeline_name: str, results: Iterable[Result]
    ) -> int:
        """Persist a collection of runtime ``results`` as a run record."""

        self.ensure_schema()
        run = self.start_run(pipeline_name)
        for result in results:
            self.record_result(run_id=run.id, result=result)
        return run.id

    # --- Utilities -----------------------------------------------------------

    def ensure_schema(self) -> None:
        Base.metadata.create_all(self.engine)

    def seed(self) -> dict[str, Any]:
        """Populate the store with a minimal demo dataset."""

        run = self.start_run("demo-pipeline")
        self.record_result(
            run_id=run.id,
            result=Result(
                message=_demo_message("demo-1", "Vitals inbound"),
                issues=[
                    Issue(severity="warning", code="temperature", message="Out-of-range value"),
                    Issue(severity="passed", code="structure"),
                ],
            ),
        )
        self.record_result(
            run_id=run.id,
            result=Result(
                message=_demo_message("demo-2", "ADT update"),
                issues=[Issue(severity="error", code="segment", message="Missing PV1 segment")],
            ),
        )
        return self.summaries()


def _encode_payload(raw: bytes) -> str:
    if isinstance(raw, bytes):
        return base64.b64encode(raw).decode("ascii")
    if isinstance(raw, str):
        return raw
    return base64.b64encode(bytes(str(raw), "utf-8")).decode("ascii")


def _issue_to_record(message_id: int, issue: Issue) -> IssueRecord:
    return IssueRecord(
        message_id=message_id,
        severity=issue.severity,
        code=issue.code,
        segment=issue.segment,
        field=str(issue.field) if issue.field is not None else None,
        component=str(issue.component) if issue.component is not None else None,
        subcomponent=str(issue.subcomponent) if issue.subcomponent is not None else None,
        value=issue.value,
        message_text=issue.message,
    )


def _demo_message(message_id: str, text: str) -> "Message":
    from engine.contracts import Message

    return Message(id=message_id, raw=text.encode("utf-8"))


_store: InsightsStore | None = None


def get_store(url: str | None = None) -> InsightsStore:
    global _store
    if _store is None or url:
        _store = InsightsStore.from_env(url=url)
    return _store


def seed(url: str | None = None) -> dict[str, Any]:
    store = get_store(url=url)
    store.ensure_schema()
    return store.seed()


def reset_store() -> None:
    """Clear the cached store instance (useful for tests)."""

    global _store
    _store = None


if __name__ == "__main__":
    summary = seed()
    print("Seeded insights store:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
