"""Pipeline specification models for Engine V2."""

from __future__ import annotations

from typing import Any, Dict, Mapping, MutableMapping

import yaml
from pydantic import BaseModel, Field, validator


class ComponentSpec(BaseModel):
    """Base configuration shared by adapters, operators, and sinks."""

    component: str = Field(..., alias="type", description="Registered component name")
    config: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        allow_population_by_field_name = True
        extra = "ignore"

    @validator("component")
    def _normalize_type(cls, value: str) -> str:
        return value.strip().lower()

    @property
    def type(self) -> str:
        return self.component


class RouterSpec(BaseModel):
    """Router strategy between operators and sinks."""

    strategy: str = Field("broadcast", description="Dispatch strategy name")
    config: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "ignore"

    @validator("strategy")
    def _normalize_strategy(cls, value: str) -> str:
        return value.strip().lower() or "broadcast"


class PipelineSpec(BaseModel):
    """Top-level pipeline description."""

    version: str = Field("1")
    name: str
    adapter: ComponentSpec
    operators: list[ComponentSpec] = Field(default_factory=list)
    router: RouterSpec = Field(default_factory=RouterSpec)
    sinks: list[ComponentSpec] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        allow_population_by_field_name = True
        extra = "ignore"

    @validator("version", pre=True)
    def _stringify_version(cls, value: Any) -> str:
        return str(value)

    @validator("operators", "sinks", pre=True, each_item=False)
    def _ensure_list(cls, value: Any) -> list[ComponentSpec]:  # type: ignore[override]
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            return list(value)
        return [value]


def load_pipeline_spec(data: Any) -> PipelineSpec:
    """Load and validate a pipeline specification.

    Args:
        data: YAML text, bytes, or a mapping representing the spec.
    """

    if isinstance(data, (str, bytes)):
        loaded = yaml.safe_load(data) or {}
    elif isinstance(data, Mapping):
        loaded = dict(data)
    else:
        raise TypeError("pipeline spec must be YAML text or a mapping")

    if not isinstance(loaded, MutableMapping):
        raise ValueError("pipeline spec root must be a mapping")

    if hasattr(PipelineSpec, "model_validate"):
        return PipelineSpec.model_validate(loaded)  # type: ignore[attr-defined]
    return PipelineSpec.parse_obj(loaded)


def dump_pipeline_spec(spec: PipelineSpec) -> Dict[str, Any]:
    """Return a normalized dictionary representation."""

    if hasattr(spec, "model_dump"):
        return spec.model_dump(by_alias=True, exclude_none=True)  # type: ignore[attr-defined]
    return spec.dict(by_alias=True, exclude_none=True)
