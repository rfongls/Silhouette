"""De-identification operator that wraps the legacy HL7 rules engine."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from silhouette_core.interop.deid import apply_single_rule

from ..contracts import Issue, Message, Operator, Result
from ..registry import register_operator

_SUPPORTED_ACTIONS = {
    "redact",
    "remove",
    "mask",
    "hash",
    "replace",
    "preset",
    "regex_replace",
    "regex_redact",
}


def _normalize_action(value: Any) -> tuple[str, Any]:
    if isinstance(value, Mapping):
        action = str(value.get("action") or "").strip().lower()
        param = value.get("param")
        return action, param
    if value is None:
        return "redact", None
    text = str(value).strip()
    if ":" in text:
        action, param = text.split(":", 1)
    else:
        action, param = text, None
    return action.lower(), param


def _parse_selector(selector: str) -> tuple[str, int, int | None, int | None]:
    if "-" not in selector:
        raise ValueError(f"Selector '{selector}' must include a segment and field index")
    segment, remainder = selector.split("-", 1)
    segment = segment.strip().upper()
    if not segment:
        raise ValueError("Segment name cannot be empty")
    pieces = [part.strip() for part in remainder.split(".") if part.strip()]
    if not pieces:
        raise ValueError(f"Selector '{selector}' requires a field position")
    try:
        field = int(pieces[0])
    except ValueError as exc:
        raise ValueError(f"Field position in selector '{selector}' must be numeric") from exc
    component = int(pieces[1]) if len(pieces) > 1 else None
    subcomponent = int(pieces[2]) if len(pieces) > 2 else None
    return segment, field, component, subcomponent


@dataclass
class DeidentifyOperator(Operator):
    """Apply HL7 de-identification rules compatible with the legacy engine."""

    name: str
    actions: Mapping[str, Any] = field(default_factory=dict)
    mode: str = "copy"

    async def process(self, msg: Message) -> Result:
        original_text = msg.raw.decode("utf-8", errors="replace")
        updated_text = original_text
        issues: list[Issue] = []
        applied = 0

        for selector, action_value in self.actions.items():
            try:
                segment, field, component, subcomponent = _parse_selector(str(selector))
            except ValueError as exc:
                issues.append(
                    Issue(
                        severity="error",
                        code="deidentify.selector.invalid",
                        value=str(selector),
                        message=str(exc),
                    )
                )
                continue

            action, param = _normalize_action(action_value)
            normalized_action = "redact" if action in {"remove", "redact"} else action
            if normalized_action not in _SUPPORTED_ACTIONS:
                issues.append(
                    Issue(
                        severity="warning",
                        code="deidentify.action.unsupported",
                        segment=segment,
                        field=field,
                        component=component,
                        subcomponent=subcomponent,
                        message=f"Unsupported action '{action}'",
                    )
                )
                continue

            rule = {
                "segment": segment,
                "field": field,
                "component": component,
                "subcomponent": subcomponent,
                "action": normalized_action,
                "param": param,
            }

            result = await asyncio.to_thread(apply_single_rule, updated_text, rule)
            updated_text = result.get("message_after", updated_text)
            if result.get("changed"):
                applied += 1
                issues.append(
                    Issue(
                        severity="passed",
                        code="deidentify.applied",
                        segment=segment,
                        field=field,
                        component=component,
                        subcomponent=subcomponent,
                        value=str(result.get("after")) if result.get("after") is not None else None,
                        message=f"Applied '{normalized_action}' to {segment}-{field}",
                    )
                )
            else:
                issues.append(
                    Issue(
                        severity="warning",
                        code="deidentify.no_change",
                        segment=segment,
                        field=field,
                        component=component,
                        subcomponent=subcomponent,
                        message="Selector did not match any values",
                    )
                )

        summary = Issue(
            severity="passed",
            code="deidentify.applied",
            message=f"Applied {applied} action(s)",
        )
        issues.append(summary)

        meta = dict(msg.meta or {})
        meta["deidentified"] = True
        if self.actions:
            meta["actions"] = dict(self.actions)
        meta["deidentify_mode"] = self.mode

        updated_raw = updated_text.encode("utf-8")
        if self.mode == "inplace":
            msg.raw = updated_raw
            msg.meta = meta
            result_msg = msg
        else:
            result_msg = Message(id=msg.id, raw=updated_raw, meta=meta)

        return Result(message=result_msg, issues=issues)


@register_operator("deidentify")
def _deidentify_operator(config: Mapping[str, object]) -> Operator:
    actions = config.get("actions") or {}
    if not isinstance(actions, Mapping):
        raise TypeError("deidentify.actions must be a mapping of selectors to actions")
    mode_raw = str(config.get("mode") or "copy").strip().lower()
    mode = mode_raw if mode_raw in {"copy", "inplace"} else "copy"
    return DeidentifyOperator(name="deidentify", actions=actions, mode=mode)
