#!/usr/bin/env python
from __future__ import annotations
import argparse, platform, subprocess, sys
from pathlib import Path

EXTRAS = {
    "core": "",
    "runtime": "[runtime]",
    "ml": "[ml]",
    "dev": "[dev]",
    "eval": "[eval]",
    "validate": "[validate]",
    "fhir": "[fhir]",
    "all": "[runtime,ml,dev,eval,validate,fhir]",
}

def venv_python(repo: Path) -> Path:
    win = platform.system() == "Windows"
    return repo / (".venv/Scripts/python.exe" if win else ".venv/bin/python")

def ensure_venv(repo: Path) -> None:
    if not (repo / ".venv").exists():
        print("[*] Creating virtualenv .venv …", flush=True)
        subprocess.check_call([sys.executable, "-m", "venv", ".venv"], cwd=str(repo))

def pip(venv_py: Path, repo: Path, *args: str) -> None:
    cmd = [str(venv_py), "-m", "pip", *args]
    print("[pip]", " ".join(args), flush=True)
    subprocess.check_call(cmd, cwd=str(repo))

def start_hapi() -> None:
    try:
        subprocess.check_call(["docker", "version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        print("[!] Docker not available; skipping HAPI", flush=True)
        return
    names = subprocess.run(["docker","ps","-a","--format","{{.Names}}"], capture_output=True, text=True).stdout.splitlines()
    if "hapi-fhir" in names:
        subprocess.call(["docker", "start", "hapi-fhir"])
        print("[*] HAPI started (existing container)")
    else:
        subprocess.call(["docker","run","-d","--name","hapi-fhir","-p","8080:8080","hapiproject/hapi:latest"])
        print("[*] HAPI launched on :8080")

def smoke_checks(venv_py: Path, repo: Path, skill: str) -> None:
    subprocess.check_call([str(venv_py), "-m", "silhouette_core.cli", "--version"], cwd=str(repo))
    if skill == "fhir":
        subprocess.check_call([str(venv_py), "-m", "silhouette_core.cli", "fhir", "validate", "-h"], cwd=str(repo))

def interactive_pick(prompt: str, options: list[str], default_idx: int = 0) -> str:
    print(prompt)
    for i, opt in enumerate(options, 1):
        print(f"  {i}) {opt}")
    sel = input(f"Select [1-{len(options)}] (default {default_idx+1}): ").strip()
    if not sel: return options[default_idx]
    try: return options[int(sel)-1]
    except Exception: return options[default_idx]

def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="One-click Silhouette setup")
    p.add_argument("--skill", choices=list(EXTRAS.keys()), help="Skill extras to install")
    p.add_argument("--with-hapi", action="store_true", help="Start local HAPI (Docker) after install")
    p.add_argument("--yes", "-y", action="store_true", help="Non-interactive; accept defaults")
    p.add_argument("--repo", type=Path, default=Path("."), help="Repo path (default: current)")
    args = p.parse_args(argv)

    repo = args.repo.resolve()
    if not (repo / "pyproject.toml").exists() and not (repo / "setup.cfg").exists():
        print("[x] Missing pyproject.toml/setup.cfg at repo root.", file=sys.stderr)
        return 2

    skill = args.skill
    with_hapi = args.with_hapi
    if not args.yes and not skill:
        skill = interactive_pick("Which skill do you want to set up?",
                                 ["fhir","validate","core","runtime","ml","dev","eval","all"], 0)
        yn = input("Start local HAPI (Docker) after install? [y/N]: ").strip().lower()
        with_hapi = (yn == "y")
    if not skill: skill = "fhir"

    ensure_venv(repo)
    vpy = venv_python(repo)
    if not vpy.exists():
        print("[x] venv Python not found", file=sys.stderr)
        return 2

    pip(vpy, repo, "install", "--upgrade", "pip")
    extras = EXTRAS[skill]
    print(f"[*] Installing -e .{extras or ''} …")
    pip(vpy, repo, "install", "-e", f".{extras}")

    print("[*] Smoke checks …")
    smoke_checks(vpy, repo, skill)

    if with_hapi:
        print("[*] Starting HAPI …")
        start_hapi()

    print("\n[OK] Setup complete.")
    print(f"- Virtualenv: {repo / '.venv'}")
    print("- To activate and use the CLI:\n")
    if platform.system() == "Windows":
        print(rf"  {repo}\.venv\Scripts\activate && silhouette --version")
    else:
        print(rf"  source {repo}/.venv/bin/activate && silhouette --version")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
