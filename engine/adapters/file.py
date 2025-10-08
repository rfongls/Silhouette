"""File-backed adapter for local testing workflows."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, Iterable, Mapping

from ..contracts import Adapter, Message
from ..registry import register_adapter


@dataclass
class FileAdapter(Adapter):
    """Stream newline-delimited HL7 payloads from one or more files."""

    name: str
    paths: Sequence[Path]
    encoding: str = "utf-8"
    delimiter: str = "\n\n"

    async def stream(self) -> AsyncIterator[Message]:
        for path in self.paths:
            if not path.exists():
                continue
            text = path.read_text(encoding=self.encoding)
            for idx, payload in enumerate(_split_messages(text, self.delimiter), start=1):
                await asyncio.sleep(0)
                yield Message(
                    id=f"{path.stem}-{idx}",
                    raw=payload.encode(self.encoding),
                    meta={"source": str(path)},
                )


def _split_messages(text: str, delimiter: str) -> Iterable[str]:
    if not text:
        return []
    if delimiter == "\n\n":
        parts = [segment.strip() for segment in text.split(delimiter)]
        return [segment for segment in parts if segment]
    return [segment for segment in text.split(delimiter) if segment]


@register_adapter("file")
def _file_adapter(config: Mapping[str, object]) -> Adapter:
    paths = _extract_paths(config)
    encoding = str(config.get("encoding") or "utf-8")
    delimiter = str(config.get("delimiter") or "\n\n")
    return FileAdapter(name="file", paths=paths, encoding=encoding, delimiter=delimiter)


def _extract_paths(config: Mapping[str, object]) -> Sequence[Path]:
    raw_paths = config.get("paths") or config.get("path")
    if raw_paths is None:
        raise ValueError("file adapter requires a 'path' or 'paths' configuration")
    if isinstance(raw_paths, (str, Path)):
        candidates = [raw_paths]
    elif isinstance(raw_paths, Sequence):
        candidates = list(raw_paths)
    else:
        raise TypeError("paths must be a string or sequence of paths")
    resolved = [Path(path).expanduser() for path in candidates]
    return tuple(resolved)
