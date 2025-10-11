"""SQLAlchemy models backing the Engine insights store."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class RunRecord(Base):
    __tablename__ = "engine_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pipeline_name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    messages: Mapped[list["MessageRecord"]] = relationship("MessageRecord", back_populates="run")


class MessageRecord(Base):
    __tablename__ = "engine_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("engine_runs.id", ondelete="CASCADE"), nullable=False)
    message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    run: Mapped[RunRecord] = relationship("RunRecord", back_populates="messages")
    issues: Mapped[list["IssueRecord"]] = relationship("IssueRecord", back_populates="message")


class IssueRecord(Base):
    __tablename__ = "engine_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("engine_messages.id", ondelete="CASCADE"), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    code: Mapped[str] = mapped_column(String(120), nullable=False)
    segment: Mapped[str | None] = mapped_column(String(40))
    field: Mapped[str | None] = mapped_column(String(40))
    component: Mapped[str | None] = mapped_column(String(40))
    subcomponent: Mapped[str | None] = mapped_column(String(40))
    value: Mapped[str | None] = mapped_column(Text)
    message_text: Mapped[str | None] = mapped_column("message", Text)

    message: Mapped[MessageRecord] = relationship("MessageRecord", back_populates="issues")


class PipelineRecord(Base):
    __tablename__ = "pipelines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    yaml: Mapped[str] = mapped_column(Text, nullable=False)
    spec: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class JobRecord(Base):
    __tablename__ = "engine_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    pipeline_id: Mapped[int] = mapped_column(
        ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)

    status: Mapped[str] = mapped_column(String(16), default="queued", nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    leased_by: Mapped[str | None] = mapped_column(String(64))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime)

    run_id: Mapped[int | None] = mapped_column(
        ForeignKey("engine_runs.id"), nullable=True
    )
    dedupe_key: Mapped[str | None] = mapped_column(String(255), unique=True)

    last_error: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    pipeline: Mapped["PipelineRecord"] = relationship("PipelineRecord")
    run: Mapped["RunRecord"] = relationship("RunRecord")


class EndpointRecord(Base):
    __tablename__ = "engine_endpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    pipeline_id: Mapped[int | None] = mapped_column(
        ForeignKey("pipelines.id", ondelete="SET NULL"), nullable=True
    )
    config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default={})
    status: Mapped[str] = mapped_column(String(16), default="stopped", nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
