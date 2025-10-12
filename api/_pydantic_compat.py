"""Compatibility helpers for supporting both Pydantic v1 and v2."""

from __future__ import annotations

from typing import Any, Callable, Set, TypeVar

from pydantic import BaseModel

F = TypeVar("F", bound=Callable[..., Any])

try:  # pragma: no cover - prefer Pydantic v2 API when available
    from pydantic import field_validator as _field_validator

    def compat_validator(field: str, *, pre: bool = False, always: bool = False) -> Callable[[F], F]:
        """Return a decorator that works across Pydantic versions."""

        mode = "before" if pre else "after"

        def decorator(func: F) -> F:
            return _field_validator(field, mode=mode)(func)  # type: ignore[misc]

        return decorator

except ImportError:  # pragma: no cover - fall back to Pydantic v1
    from pydantic import validator as _validator  # type: ignore

    def compat_validator(field: str, *, pre: bool = False, always: bool = False) -> Callable[[F], F]:
        return _validator(field, pre=pre, always=always)


def fields_set(model: BaseModel) -> Set[str]:
    """Return the set of fields supplied by the caller across Pydantic versions."""

    if hasattr(model, "model_fields_set"):
        return set(getattr(model, "model_fields_set"))  # type: ignore[attr-defined]
    return set(getattr(model, "__fields_set__", set()))
