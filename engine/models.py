"""Lightweight ORM models for Engine interfaces and endpoints (SQLAlchemy 2.x style)."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base class for Engine models."""

    pass


class Direction(str, Enum):
    """Interface traffic direction."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"


class Protocol(str, Enum):
    """Supported endpoint transport protocols."""

    MLLP = "mllp"
    HTTP = "http"
    FILEDROP = "filedrop"


class EngineInterface(Base):
    """An inbound or outbound interface managed by the Engine."""

    __tablename__ = "engine_interfaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pipeline_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    endpoints: Mapped[list["Endpoint"]] = relationship(
        "Endpoint",
        back_populates="interface",
        cascade="all, delete-orphan",
        order_by="Endpoint.id",
    )


class Endpoint(Base):
    """Connection details for a specific Engine interface."""

    __tablename__ = "engine_endpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    interface_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("engine_interfaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    protocol: Mapped[str] = mapped_column(String(16), nullable=False)
    host: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    interface: Mapped["EngineInterface"] = relationship(
        "EngineInterface",
        back_populates="endpoints",
    )
