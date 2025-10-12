"""Execution helpers for Engine V2 pipelines."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, Iterable

from . import plugins  # noqa: F401  # ensure built-ins and stubs registered
from .contracts import Adapter, Issue, Message, Operator, Result, Sink
from .registry import create_adapter, create_operator, create_sink
from .spec import ComponentSpec, PipelineSpec

ResultWriter = Callable[[Result], Awaitable[None]]


class PipelineRuntime:
    """In-process runtime for a single pipeline."""

    def __init__(
        self,
        *,
        spec: PipelineSpec,
        adapter: Adapter,
        operators: Iterable[Operator],
        sinks: Iterable[Sink],
        persist_result: ResultWriter | None = None,
    ) -> None:
        self.spec = spec
        self.adapter = adapter
        self.operators = list(operators)
        self.sinks = list(sinks)
        self._persist_result = persist_result

    async def run(self, *, max_messages: int | None = 1) -> list[Result]:
        """Execute the pipeline for ``max_messages`` messages."""

        results: list[Result] = []
        count = 0
        async for message in self._iterate_messages():
            result = await self._process_message(message)
            await self._dispatch(result)
            if self._persist_result:
                await self._persist_result(result)
            results.append(result)
            count += 1
            if max_messages is not None and count >= max_messages:
                break
        return results

    async def _iterate_messages(self) -> AsyncIterator[Message]:
        async for message in self.adapter.stream():
            yield message

    async def _process_message(self, message: Message) -> Result:
        current = message
        collected: list[Issue] = []
        for operator in self.operators:
            result = await operator.process(current)
            current = result.message
            collected.extend(result.issues)
        return Result(message=current, issues=collected)

    async def _dispatch(self, result: Result) -> None:
        for sink in self.sinks:
            await sink.write(result)


class EngineRuntime:
    """Helper to construct ``PipelineRuntime`` instances from specs or operator chains."""

    def __init__(
        self,
        spec: PipelineSpec | None = None,
        persist_result: ResultWriter | None = None,
        *,
        operators: Iterable[Any] | None = None,
    ) -> None:
        if spec is None and not operators:
            raise ValueError("spec or operators must be provided")
        self.spec = spec
        self.persist_result = persist_result
        self.pipeline = self._build_pipeline() if spec is not None else None
        self._operators = list(operators or [])

    def _build_pipeline(self) -> PipelineRuntime:
        adapter = _instantiate_component(self.spec.adapter, create_adapter)
        operators = [_instantiate_component(op, create_operator) for op in self.spec.operators]
        sinks = [_instantiate_component(sink, create_sink) for sink in self.spec.sinks]
        return PipelineRuntime(
            spec=self.spec,
            adapter=adapter,
            operators=operators,
            sinks=sinks,
            persist_result=self.persist_result,
        )

    async def run(self, *, max_messages: int | None = 1) -> list[Result]:
        if not self.pipeline:
            raise RuntimeError("runtime does not have a pipeline spec configured")
        return await self.pipeline.run(max_messages=max_messages)

    async def run_on_message(self, message_bytes: bytes) -> bytes:
        if not self._operators:
            return message_bytes

        class _Message:
            __slots__ = ("raw",)

            def __init__(self, data: bytes) -> None:
                self.raw = data

        msg = _Message(message_bytes)
        for operator in self._operators:
            msg = operator.apply(msg)
        return msg.raw


def _instantiate_component(
    component: ComponentSpec,
    factory: Callable[[str, dict[str, Any]], Any],
):
    return factory(component.type, component.config)


