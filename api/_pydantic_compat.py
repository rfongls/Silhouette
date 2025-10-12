"""Compatibility helpers for supporting both Pydantic v1 and v2."""

from __future__ import annotations

from typing import Any, Callable, Set, TypeVar

from pydantic import BaseModel

F = TypeVar("F", bound=Callable[..., Any])

try:  # pragma: no cover - prefer Pydantic v2 API when available
    from pydantic import field_validator as _field_validator

    def compat_validator(*fields: str, pre: bool = False, always: bool = False) -> Callable[[F], F]:
        """Return a decorator that works across Pydantic versions.

        Parameters mirror the common subset between Pydantic v1 ``@validator`` and
        v2 ``@field_validator`` so existing validators can opt into the helper
        without branching. When ``always`` is ``True`` we default to ``before``
        mode which matches the v1 behaviour of running even if a field is
        missing from the payload.
        """

        if not fields:
            raise ValueError("compat_validator requires at least one field name")

        mode = "before" if pre or always else "after"

        def decorator(func: F) -> F:
            return _field_validator(*fields, mode=mode)(func)  # type: ignore[misc]

        return decorator

except ImportError:  # pragma: no cover - fall back to Pydantic v1
    from pydantic import validator as _validator  # type: ignore

    def compat_validator(*fields: str, pre: bool = False, always: bool = False) -> Callable[[F], F]:
        if not fields:
            raise ValueError("compat_validator requires at least one field name")
        return _validator(*fields, pre=pre, always=always)


def fields_set(model: BaseModel) -> Set[str]:
    """Return the set of fields supplied by the caller across Pydantic versions."""

    if hasattr(model, "model_fields_set"):
        return set(getattr(model, "model_fields_set"))  # type: ignore[attr-defined]
    return set(getattr(model, "__fields_set__", set()))
