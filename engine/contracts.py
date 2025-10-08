"""Core data contracts for the Engine runtime."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Literal


@dataclass(slots=True)
class Message:
    """A payload emitted by an adapter."""

    id: str
    raw: bytes
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Issue:
    """A structured finding emitted by an operator."""

    severity: Literal["error", "warning", "passed"]
    code: str
    segment: str | None = None
    field: str | int | None = None
    component: str | int | None = None
    subcomponent: str | int | None = None
    value: str | None = None
    message: str | None = None


@dataclass(slots=True)
class Result:
    """An operator result containing the message and emitted issues."""

    message: Message
    issues: list[Issue] = field(default_factory=list)


class Adapter(ABC):
    """Adapters bridge external sources into message streams."""

    name: str

    @abstractmethod
    async def stream(self) -> AsyncIterator[Message]:
        """Produce messages for downstream operators."""


class Operator(ABC):
    """Operators transform or analyze messages."""

    name: str

    @abstractmethod
    async def process(self, msg: Message) -> Result:
        """Process ``msg`` and return a structured ``Result``."""


class Sink(ABC):
    """Sinks receive processed results."""

    name: str

    @abstractmethod
    async def write(self, result: Result) -> None:
        """Persist or forward the ``result`` to an external system."""
