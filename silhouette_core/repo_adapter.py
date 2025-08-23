"""Minimal repository adapter abstractions for Silhouette.

This module introduces the :class:`RepoAdapter` interface together with a
basic :class:`LocalRepoAdapter` implementation.  The adapter is intentionally
minimal and currently focuses on local, read-only repositories.  Future work
will extend this to support remote Git hosts, sparse checkout, and write
operations as described in the roadmap.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


class RepoAdapter:
    """Abstract interface for repository operations.

    Implementations are responsible for fetching sources, listing files and
    reading or writing text content.  The default policy is read‑only; callers
    must explicitly opt in to any write capability.
    """

    def fetch(self, source: str, ref: Optional[str] = None, sparse: Optional[List[str]] = None) -> str:
        """Fetch ``source`` and return a local path.

        Parameters
        ----------
        source:
            A path or URL pointing to the repository.
        ref:
            Optional branch or commit reference.
        sparse:
            Optional list of glob patterns specifying a sparse checkout.
        """
        raise NotImplementedError

    def list_files(self, patterns: List[str]) -> List[str]:
        """Return repository files matching any of the given glob ``patterns``."""
        raise NotImplementedError

    def read_text(self, path: str) -> str:
        """Read a text file from the repository."""
        raise NotImplementedError

    def write_text(self, path: str, content: str) -> None:
        """Write text to ``path`` inside the repository.

        Implementations may raise :class:`PermissionError` when operating in
        read‑only mode.
        """
        raise NotImplementedError

    def open_pr(self, title: str, body: str, branch: str, base: str = "main") -> str:
        """Open a pull request and return its URL.

        This operation is only meaningful for adapters backed by hosted Git
        services.  ``LocalRepoAdapter`` leaves this unimplemented.
        """
        raise NotImplementedError


@dataclass
class LocalRepoAdapter(RepoAdapter):
    """Simple adapter for local file system repositories."""

    root: Path
    read_only: bool = True

    def fetch(self, source: str, ref: Optional[str] = None, sparse: Optional[List[str]] = None) -> str:
        path = Path(source)
        self.root = path.resolve()
        # Sparse checkout is not implemented yet; callers may provide patterns
        # which are currently ignored.
        return str(self.root)

    def list_files(self, patterns: List[str]) -> List[str]:
        def _match(rel: Path, pattern: str) -> bool:
            if rel.match(pattern):
                return True
            if pattern.startswith("**/") and rel.match(pattern[3:]):
                return True
            return False

        files: List[str] = []
        for p in self.root.rglob('*'):
            if p.is_file():
                rel = p.relative_to(self.root)
                if any(_match(rel, pat) for pat in patterns):
                    files.append(str(rel))
        return sorted(files)

    def read_text(self, path: str) -> str:
        return (self.root / path).read_text(encoding="utf-8")

    def write_text(self, path: str, content: str) -> None:
        if self.read_only:
            raise PermissionError("adapter is read-only")
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def open_pr(self, title: str, body: str, branch: str, base: str = "main") -> str:
        raise NotImplementedError("Local repositories cannot open pull requests")
