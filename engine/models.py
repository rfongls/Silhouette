"""Lightweight ORM models for Engine interfaces and endpoints."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


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

    id: int = Column(Integer, primary_key=True)
    name: str = Column(String(120), unique=True, nullable=False)
    direction: str = Column(String(16), nullable=False)
    description: Optional[str] = Column(Text, nullable=True)
    pipeline_id: Optional[str] = Column(String(120), nullable=True)
    is_active: bool = Column(Boolean, default=False)
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)

    endpoints: List["Endpoint"] = relationship(
        "Endpoint",
        back_populates="interface",
        cascade="all, delete-orphan",
        order_by="Endpoint.id",
    )


class Endpoint(Base):
    """Connection details for a specific Engine interface."""

    __tablename__ = "engine_endpoints"

    id: int = Column(Integer, primary_key=True)
    interface_id: int = Column(Integer, ForeignKey("engine_interfaces.id", ondelete="CASCADE"), nullable=False)
    protocol: str = Column(String(16), nullable=False)
    host: Optional[str] = Column(String(255), nullable=True)
    port: Optional[int] = Column(Integer, nullable=True)
    path: Optional[str] = Column(String(512), nullable=True)
    notes: Optional[str] = Column(Text, nullable=True)

    interface: EngineInterface = relationship("EngineInterface", back_populates="endpoints")
