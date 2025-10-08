"""Registration utilities for engine components."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Dict, Mapping, MutableMapping, TypeVar

from .contracts import Adapter, Operator, Sink

AdapterFactory = Callable[[Mapping[str, Any]], Adapter]
OperatorFactory = Callable[[Mapping[str, Any]], Operator]
SinkFactory = Callable[[Mapping[str, Any]], Sink]


_T = TypeVar("_T")


class _ComponentRegistry:
    """Internal helper tracking registered factories."""

    def __init__(self) -> None:
        self._registry: MutableMapping[str, Callable[[Mapping[str, Any]], Any]] = {}

    def register(self, name: str, factory: Callable[[Mapping[str, Any]], _T]) -> Callable[[Mapping[str, Any]], _T]:
        key = name.lower().strip()
        if not key:
            raise ValueError("component name must be non-empty")
        if key in self._registry:
            raise ValueError(f"component {name!r} already registered")
        self._registry[key] = factory
        return factory

    def create(self, name: str, config: Mapping[str, Any]) -> _T:
        key = name.lower().strip()
        try:
            factory = self._registry[key]
        except KeyError as exc:
            raise KeyError(f"unknown component {name!r}") from exc
        return factory(config)

    def registered(self) -> Dict[str, Callable[[Mapping[str, Any]], Any]]:
        return dict(self._registry)

    def clear(self) -> None:
        self._registry.clear()


_adapters = _ComponentRegistry()
_operators = _ComponentRegistry()
_sinks = _ComponentRegistry()


def register_adapter(name: str) -> Callable[[AdapterFactory], AdapterFactory]:
    """Decorator to register an adapter factory."""

    def decorator(factory: AdapterFactory) -> AdapterFactory:
        return _adapters.register(name, factory)

    return decorator


def register_operator(name: str) -> Callable[[OperatorFactory], OperatorFactory]:
    """Decorator to register an operator factory."""

    def decorator(factory: OperatorFactory) -> OperatorFactory:
        return _operators.register(name, factory)

    return decorator


def register_sink(name: str) -> Callable[[SinkFactory], SinkFactory]:
    """Decorator to register a sink factory."""

    def decorator(factory: SinkFactory) -> SinkFactory:
        return _sinks.register(name, factory)

    return decorator


def create_adapter(name: str, config: Mapping[str, Any]) -> Adapter:
    return _adapters.create(name, config)


def create_operator(name: str, config: Mapping[str, Any]) -> Operator:
    return _operators.create(name, config)


def create_sink(name: str, config: Mapping[str, Any]) -> Sink:
    return _sinks.create(name, config)


def dump_registry() -> dict[str, dict[str, str]]:
    """Return the registry contents for diagnostics."""

    def to_names(src: Dict[str, Callable[[Mapping[str, Any]], Any]]) -> dict[str, str]:
        return {name: f"{factory.__module__}.{factory.__qualname__}" for name, factory in src.items()}

    return {
        "adapters": to_names(_adapters.registered()),
        "operators": to_names(_operators.registered()),
        "sinks": to_names(_sinks.registered()),
    }


def reset_registry() -> None:
    """Reset all registries — useful for isolated tests."""

    _adapters.clear()
    _operators.clear()
    _sinks.clear()
