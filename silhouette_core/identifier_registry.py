"""Identifier system registry loader."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import yaml

@lru_cache
def _load_registry() -> dict[str, str]:
    path = Path("config/identifier_systems.yaml")
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {str(k): str(v) for k, v in data.items()}


def get_system(name: str) -> str | None:
    """Return canonical system URI for a given identifier key."""
    return _load_registry().get(name)
