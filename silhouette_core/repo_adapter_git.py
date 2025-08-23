from __future__ import annotations
import subprocess
from collections.abc import Iterable
from pathlib import Path

from .repo_adapter import RepoAdapter


class GitRepoAdapter(RepoAdapter):
    """Git-backed repository adapter in read-only mode by default."""

    def __init__(self, workdir: Path, enable_write: bool = False) -> None:
        self.workdir = workdir
        self.enable_write = enable_write
        self.root: Path | None = None

    # fetch
    def fetch(self, source: str, ref: str | None = None, sparse: list[str] | None = None) -> str:
        self.workdir.mkdir(parents=True, exist_ok=True)
        if not (self.workdir / ".git").exists():
            subprocess.check_call([
                "git",
                "clone",
                "--depth",
                "1",
                source,
                str(self.workdir),
            ])
        if sparse:
            subprocess.check_call([
                "git",
                "-C",
                str(self.workdir),
                "sparse-checkout",
                "init",
                "--cone",
            ])
            subprocess.check_call([
                "git",
                "-C",
                str(self.workdir),
                "sparse-checkout",
                "set",
                *sparse,
            ])
        if ref:
            subprocess.check_call(["git", "-C", str(self.workdir), "checkout", ref])
        self.root = self.workdir.resolve()
        return str(self.root)

    # list_files
    def list_files(self, patterns: Iterable[str] | None = None) -> list[str]:
        assert self.root is not None, "repository not fetched"
        result = subprocess.check_output(
            ["git", "-C", str(self.root), "ls-files"], text=True
        )
        files = result.splitlines()
        if not patterns:
            return sorted(files)
        includes = [p for p in patterns if not p.startswith("!")]
        excludes = [p[1:] for p in patterns if p.startswith("!")]
        selected: list[str] = []
        for f in files:
            p = Path(f)
            if includes and not any(p.match(pat) for pat in includes):
                continue
            if any(p.match(pat) for pat in excludes):
                continue
            selected.append(f)
        return sorted(selected)

    # read_text
    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        assert self.root is not None, "repository not fetched"
        return (self.root / path).read_text(encoding=encoding)

    # write_text
    def write_text(self, path: str, content: str, encoding: str = "utf-8") -> None:
        if not self.enable_write:
            raise PermissionError("adapter is read-only")
        assert self.root is not None, "repository not fetched"
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding=encoding)

    # open_pr
    def open_pr(self, title: str, body: str, branch: str, base: str = "main") -> str:
        raise NotImplementedError("GitRepoAdapter cannot open pull requests in this version")
