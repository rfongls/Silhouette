"""Shared type aliases and helpers for API request/response schemas."""

from __future__ import annotations
from typing import Literal, Tuple, get_args

EndpointKind = Literal["mllp_in", "mllp_out"]
SinkKind = Literal["folder", "db"]
PipelineScope = Literal["engine", "endpoint"]
ProfileKind = Literal["transform", "deid", "validate"]
JobKind = Literal["run", "replay"]


def _literal_values(lit: object) -> set[str]:
    """Return the runtime set of valid values for a ``Literal`` type."""

    return set(get_args(lit))  # type: ignore[arg-type]


ENDPOINT_KIND_VALUES = _literal_values(EndpointKind)
SINK_KIND_VALUES = _literal_values(SinkKind)
PIPELINE_SCOPE_VALUES = _literal_values(PipelineScope)
PROFILE_KIND_VALUES = _literal_values(ProfileKind)
JOB_KIND_VALUES = _literal_values(JobKind)

__all__: Tuple[str, ...] = (
    "EndpointKind",
    "SinkKind",
    "PipelineScope",
    "ProfileKind",
    "JobKind",
    "ENDPOINT_KIND_VALUES",
    "SINK_KIND_VALUES",
    "PIPELINE_SCOPE_VALUES",
    "PROFILE_KIND_VALUES",
    "JOB_KIND_VALUES",
)
