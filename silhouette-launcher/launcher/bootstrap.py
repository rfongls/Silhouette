from __future__ import annotations
import sys, subprocess
from pathlib import Path
from .platform_utils import venv_python, extras_for

def ensure_venv(repo: Path, on_line) -> None:
    """Create .venv in the target repo if absent."""
    if not (repo / ".venv").exists():
        on_line("[*] Creating virtualenv …")
        code = subprocess.call([sys.executable, "-m", "venv", ".venv"], cwd=str(repo))
        if code != 0:
            raise RuntimeError("venv creation failed")

def pip(vpy: Path, args: list[str], repo: Path, on_line) -> None:
    """Run pip with streaming logs."""
    cmd = [str(vpy), "-m", "pip"] + args
    on_line(f"[pip] {' '.join(args)}")
    proc = subprocess.Popen(cmd, cwd=str(repo), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert proc.stdout is not None
    for line in iter(proc.stdout.readline, ""):
        on_line(line.rstrip("\n"))
    proc.stdout.close()
    if proc.wait() != 0:
        raise RuntimeError("pip failed")

def start_hapi(on_line) -> None:
    """Best-effort start of a local HAPI (Docker)."""
    try:
        subprocess.check_call(["docker", "version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        on_line("[!] Docker not available; skipping HAPI")
        return
    names = subprocess.run(
        ["docker", "ps", "-a", "--format", "{{.Names}}"], capture_output=True, text=True
    ).stdout.splitlines()
    if "hapi-fhir" in names:
        subprocess.call(["docker", "start", "hapi-fhir"])
        on_line("[*] HAPI started (existing container)")
    else:
        subprocess.call(["docker", "run", "-d", "--name", "hapi-fhir", "-p", "8080:8080", "hapiproject/hapi:latest"])
        on_line("[*] HAPI launched on port 8080")

def smoke_checks(vpy: Path, skill: str, repo: Path, on_line) -> None:
    """Basic CLI checks to ensure install worked."""
    if subprocess.call([str(vpy), "-m", "silhouette_core.cli", "--version"], cwd=str(repo)) != 0:
        raise RuntimeError("silhouette CLI not importable in venv")
    if skill == "fhir":
        if subprocess.call([str(vpy), "-m", "silhouette_core.cli", "fhir", "validate", "-h"], cwd=str(repo)) != 0:
            raise RuntimeError("FHIR validators not available")

def bootstrap(repo: Path, skill: str, with_hapi: bool, on_line) -> None:
    """End-to-end setup for a selected skill in a selected repo."""
    on_line(f"[*] Repo: {repo}")
    if not (repo / "pyproject.toml").exists() and not (repo / "setup.cfg").exists():
        raise RuntimeError("Selected folder does not look like a Python project (missing pyproject.toml/setup.cfg)")
    ensure_venv(repo, on_line)
    vpy = venv_python(repo)
    if not vpy.exists():
        raise RuntimeError("venv python missing")

    # pip upgrade + editable install with extras
    pip(vpy, ["install", "--upgrade", "pip"], repo, on_line)
    extras = extras_for(skill)
    on_line(f"[*] Installing -e .{extras or ''} …")
    pip(vpy, ["install", "-e", f".{extras}"], repo, on_line)

    # smoke
    on_line("[*] Smoke checks …")
    smoke_checks(vpy, skill, repo, on_line)

    # optional HAPI
    if with_hapi:
        on_line("[*] Starting HAPI (Docker) …")
        start_hapi(on_line)

    on_line("[OK] Setup complete.")
