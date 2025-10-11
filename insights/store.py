"""High-level helpers for interacting with the insights database."""

from __future__ import annotations

import base64
import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Sequence

from sqlalchemy import and_, create_engine, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from engine.contracts import Issue, Result
from api.sql_logging import install_sql_logging

from .models import (
    Base,
    EndpointRecord,
    IssueRecord,
    JobRecord,
    MessageRecord,
    PipelineRecord,
    RunRecord,
)

_DEFAULT_DB = Path("data") / "insights.db"
_GLOBAL_STORE: "InsightsStore" | None = None


class QueueFullError(RuntimeError):
    """Raised when enqueueing a job exceeds configured back-pressure limits."""


class DuplicateJobError(RuntimeError):
    """Raised when a job with the same dedupe key already exists."""

    def __init__(self, job: JobRecord):
        super().__init__("job with dedupe key already exists")
        self.job = job
        self.job_data = _job_as_dict(job)


class JobNotFoundError(RuntimeError):
    """Raised when attempting to mutate a job that cannot be found."""


_LEASEABLE_STATUSES = {"queued", "leased"}
_CANCELABLE_STATUSES = {"queued", "leased", "running"}


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

    # --- Endpoint helpers ---------------------------------------------------

    def create_endpoint(
        self,
        *,
        kind: str,
        name: str,
        pipeline_id: int | None,
        config: dict[str, Any],
    ) -> EndpointRecord:
        now = datetime.utcnow()
        with self.session() as session:
            if pipeline_id is not None:
                pipeline = session.get(PipelineRecord, pipeline_id)
                if pipeline is None:
                    raise KeyError(f"pipeline {pipeline_id} not found")
            record = EndpointRecord(
                kind=kind,
                name=name,
                pipeline_id=pipeline_id,
                config=dict(config or {}),
                status="stopped",
                created_at=now,
                updated_at=now,
            )
            session.add(record)
            session.flush()
            session.refresh(record)
            return record

    def update_endpoint(self, endpoint_id: int, **fields: Any) -> bool:
        with self.session() as session:
            record = session.get(EndpointRecord, endpoint_id)
            if record is None:
                return False
            for key, value in fields.items():
                if not hasattr(record, key):
                    continue
                setattr(record, key, value)
            record.updated_at = datetime.utcnow()
            session.add(record)
            return True

    def delete_endpoint(self, endpoint_id: int) -> bool:
        with self.session() as session:
            record = session.get(EndpointRecord, endpoint_id)
            if record is None:
                return False
            session.delete(record)
            return True

    def get_endpoint(self, endpoint_id: int) -> EndpointRecord | None:
        with self.session() as session:
            return session.get(EndpointRecord, endpoint_id)

    def get_endpoint_by_name(self, name: str) -> EndpointRecord | None:
        with self.session() as session:
            return (
                session.execute(
                    select(EndpointRecord).where(EndpointRecord.name == name)
                )
                .scalars()
                .first()
            )

    def list_endpoints(self, *, kind: list[str] | None = None) -> list[EndpointRecord]:
        with self.session() as session:
            query = select(EndpointRecord)
            if kind:
                query = query.where(EndpointRecord.kind.in_(kind))
            return session.execute(query.order_by(EndpointRecord.id.asc())).scalars().all()

    # --- Job queue helpers ---------------------------------------------------

    def enqueue_job(
        self,
        *,
        pipeline_id: int,
        kind: str = "run",
        payload: dict[str, Any] | None = None,
        scheduled_at: datetime | None = None,
        priority: int = 0,
        max_attempts: int = 3,
        dedupe_key: str | None = None,
    ) -> JobRecord:
        scheduled = scheduled_at or datetime.utcnow()
        with self.session() as session:
            pipeline = session.get(PipelineRecord, pipeline_id)
            if pipeline is None:
                raise KeyError(f"pipeline {pipeline_id} not found")

            if dedupe_key:
                existing = (
                    session.execute(
                        select(JobRecord).where(JobRecord.dedupe_key == dedupe_key)
                    )
                    .scalars()
                    .first()
                )
                if existing is not None:
                    raise DuplicateJobError(existing)

            max_per_pipeline = _max_queued_per_pipeline()
            if max_per_pipeline is not None:
                queued_count = (
                    session.execute(
                        select(func.count(JobRecord.id)).where(
                            JobRecord.pipeline_id == pipeline_id,
                            JobRecord.status == "queued",
                        )
                    )
                    .scalar_one()
                )
                if queued_count >= max_per_pipeline:
                    raise QueueFullError(
                        f"pipeline {pipeline_id} has {queued_count} queued jobs"
                    )

            job = JobRecord(
                pipeline_id=pipeline_id,
                kind=kind,
                payload=payload,
                status="queued",
                priority=priority,
                attempts=0,
                max_attempts=max(1, max_attempts),
                scheduled_at=scheduled,
                dedupe_key=dedupe_key,
            )
            session.add(job)
            try:
                session.flush()
            except IntegrityError as exc:
                if dedupe_key:
                    existing = (
                        session.execute(
                            select(JobRecord).where(JobRecord.dedupe_key == dedupe_key)
                        )
                        .scalars()
                        .first()
                    )
                    if existing is not None:
                        raise DuplicateJobError(existing) from exc
                raise
            session.refresh(job)
            return job

    def lease_jobs(
        self,
        *,
        worker_id: str,
        now: datetime,
        lease_ttl_secs: int,
        limit: int,
    ) -> list[JobRecord]:
        if limit <= 0:
            return []

        deadline = now + timedelta(seconds=lease_ttl_secs)
        leased: list[JobRecord] = []
        with self.session() as session:
            candidate_ids = self._select_candidate_job_ids(session, now, limit)

            for job_id in candidate_ids:
                updated = (
                    session.execute(
                        update(JobRecord)
                        .where(
                            JobRecord.id == job_id,
                            JobRecord.status.in_(_LEASEABLE_STATUSES),
                            or_(
                                JobRecord.status == "queued",
                                JobRecord.lease_expires_at.is_(None),
                                JobRecord.lease_expires_at <= now,
                            ),
                        )
                        .values(
                            status="leased",
                            leased_by=worker_id,
                            lease_expires_at=deadline,
                            updated_at=now,
                        )
                    )
                ).rowcount
                if updated:
                    job = session.get(JobRecord, job_id)
                    if job is not None:
                        leased.append(job)
                if len(leased) >= limit:
                    break

            return leased

    def heartbeat_job(
        self, job_id: int, worker_id: str, now: datetime, lease_ttl_secs: int
    ) -> bool:
        deadline = now + timedelta(seconds=lease_ttl_secs)
        with self.session() as session:
            updated = (
                session.execute(
                    update(JobRecord)
                    .where(
                        JobRecord.id == job_id,
                        JobRecord.leased_by == worker_id,
                        JobRecord.status.in_({"leased", "running"}),
                    )
                    .values(lease_expires_at=deadline, updated_at=now)
                )
            ).rowcount
            return bool(updated)

    def start_job(self, job_id: int, worker_id: str, *, now: datetime) -> JobRecord | None:
        with self.session() as session:
            job = (
                session.execute(
                    select(JobRecord).where(
                        JobRecord.id == job_id,
                        JobRecord.leased_by == worker_id,
                        JobRecord.status == "leased",
                    )
                )
                .scalars()
                .first()
            )
            if job is None:
                return None
            job.status = "running"
            job.updated_at = now
            session.add(job)
            session.flush()
            session.refresh(job)
            return job

    def complete_job(self, job_id: int, run_id: int | None) -> None:
        now = datetime.utcnow()
        with self.session() as session:
            job = session.get(JobRecord, job_id)
            if job is None:
                raise JobNotFoundError(f"job {job_id} not found")
            if job.status == "canceled":
                return
            job.status = "succeeded"
            job.run_id = run_id
            job.leased_by = None
            job.lease_expires_at = None
            job.updated_at = now
            session.add(job)

    def fail_job_and_maybe_retry(
        self,
        job_id: int,
        error: str,
        now: datetime,
        backoff_secs: int,
    ) -> None:
        with self.session() as session:
            job = session.get(JobRecord, job_id)
            if job is None:
                raise JobNotFoundError(f"job {job_id} not found")

            next_attempt = job.attempts + 1
            job.attempts = next_attempt
            job.last_error = error
            job.leased_by = None
            job.lease_expires_at = None
            job.updated_at = now

            if next_attempt < job.max_attempts:
                job.status = "queued"
                job.scheduled_at = now + timedelta(seconds=max(backoff_secs, 0))
            else:
                job.status = "dead"

            session.add(job)

    def cancel_job(self, job_id: int) -> bool:
        with self.session() as session:
            job = session.get(JobRecord, job_id)
            if job is None:
                return False
            if job.status not in _CANCELABLE_STATUSES:
                return False
            job.status = "canceled"
            job.leased_by = None
            job.lease_expires_at = None
            job.updated_at = datetime.utcnow()
            session.add(job)
            return True

    def retry_job(self, job_id: int, *, now: datetime | None = None) -> bool:
        with self.session() as session:
            job = session.get(JobRecord, job_id)
            if job is None:
                return False
            if job.status not in {"dead", "canceled"}:
                return False
            job.status = "queued"
            job.attempts = 0
            job.leased_by = None
            job.lease_expires_at = None
            job.scheduled_at = (now or datetime.utcnow())
            job.updated_at = datetime.utcnow()
            session.add(job)
            return True

    def list_jobs(
        self,
        *,
        status: list[str] | None = None,
        pipeline_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[JobRecord]:
        with self.session() as session:
            query = session.query(JobRecord)
            if status:
                query = query.filter(JobRecord.status.in_(status))
            if pipeline_id is not None:
                query = query.filter(JobRecord.pipeline_id == pipeline_id)
            query = query.order_by(
                JobRecord.status.asc(),
                JobRecord.priority.desc(),
                JobRecord.scheduled_at.asc(),
                JobRecord.id.asc(),
            )
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            return list(query.all())

    def get_job(self, job_id: int) -> JobRecord | None:
        with self.session() as session:
            return session.get(JobRecord, job_id)

    def _select_candidate_job_ids(
        self, session: Session, now: datetime, limit: int
    ) -> Sequence[int]:
        return (
            session.execute(
                select(JobRecord.id)
                .where(
                    JobRecord.scheduled_at <= now,
                    or_(
                        JobRecord.status == "queued",
                        and_(
                            JobRecord.status == "leased",
                            JobRecord.lease_expires_at.isnot(None),
                            JobRecord.lease_expires_at <= now,
                        ),
                    ),
                )
                .order_by(
                    JobRecord.priority.desc(),
                    JobRecord.scheduled_at.asc(),
                    JobRecord.id.asc(),
                )
                .limit(limit * 4)
            )
            .scalars()
            .all()
        )

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


def _max_queued_per_pipeline() -> int | None:
    value = os.getenv("ENGINE_QUEUE_MAX_QUEUED_PER_PIPELINE")
    if value is None or value == "":
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return max(parsed, 0)


def _job_as_dict(job: JobRecord) -> dict[str, Any]:
    return {
        "id": job.id,
        "pipeline_id": job.pipeline_id,
        "kind": job.kind,
        "payload": job.payload,
        "status": job.status,
        "priority": job.priority,
        "attempts": job.attempts,
        "max_attempts": job.max_attempts,
        "scheduled_at": job.scheduled_at,
        "leased_by": job.leased_by,
        "lease_expires_at": job.lease_expires_at,
        "run_id": job.run_id,
        "dedupe_key": job.dedupe_key,
        "last_error": job.last_error,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


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

def get_store(url: str | None = None) -> InsightsStore:
    """Return a process-wide store instance, or construct one for a custom URL."""

    global _GLOBAL_STORE
    if url is not None:
        # Tests and utilities can request an isolated store without disturbing the
        # shared singleton.
        return InsightsStore.from_env(url=url)

    if _GLOBAL_STORE is None:
        _GLOBAL_STORE = InsightsStore.from_env()
    return _GLOBAL_STORE


def seed(url: str | None = None) -> dict[str, Any]:
    store = get_store(url=url)
    store.ensure_schema()
    return store.seed()


def reset_store() -> None:
    """Clear the cached store instance (useful for tests)."""

    global _GLOBAL_STORE
    _GLOBAL_STORE = None


if __name__ == "__main__":
    summary = seed()
    print("Seeded insights store:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
