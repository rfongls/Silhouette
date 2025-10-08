"""Stub de-identification operator for Phase 1 scaffolding."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from ..contracts import Issue, Message, Operator, Result
from ..registry import register_operator


@dataclass
class DeidentifyOperator(Operator):
    """Placeholder that annotates messages to simulate de-identification."""

    name: str
    actions: Mapping[str, str] = field(default_factory=dict)

    async def process(self, msg: Message) -> Result:
        meta = dict(msg.meta or {})
        meta["deidentified"] = True
        if self.actions:
            meta["actions"] = dict(self.actions)
        issues = [
            Issue(
                severity="passed",
                code="deidentify.stub",
                message="Applied placeholder de-identification rules",
            )
        ]
        return Result(message=Message(id=msg.id, raw=msg.raw, meta=meta), issues=issues)


@register_operator("deidentify")
def _deidentify_operator(config: Mapping[str, object]) -> Operator:
    actions = config.get("actions") or {}
    if not isinstance(actions, Mapping):
        raise TypeError("deidentify.actions must be a mapping of selectors to actions")
    return DeidentifyOperator(name="deidentify", actions=actions)
