from __future__ import annotations

import typing

# ForwardRef._evaluate gained a keyword-only 'recursive_guard' parameter in
# Python 3.12. Older callers may still supply this as a positional argument.
# This shim accepts both call styles to keep dependencies working across
# Python versions.
if hasattr(typing, "ForwardRef") and hasattr(typing.ForwardRef, "_evaluate"):
    _orig = typing.ForwardRef._evaluate

    def _wrapped(self, globalns, localns, *args, **kwargs):
        if args and "recursive_guard" not in kwargs:
            kwargs["recursive_guard"] = args[0]
        kwargs.setdefault("recursive_guard", set())
        return _orig(self, globalns, localns, **kwargs)

    typing.ForwardRef._evaluate = _wrapped  # type: ignore[attr-defined]
