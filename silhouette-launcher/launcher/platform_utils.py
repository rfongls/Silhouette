from __future__ import annotations
import platform
from pathlib import Path

def venv_python(repo: Path) -> Path:
    """Return path to venv Python inside the selected repo."""
    win = platform.system() == "Windows"
    return repo / (".venv/Scripts/python.exe" if win else ".venv/bin/python")

def extras_for(skill: str) -> str:
    """Map skill name to pip extras."""
    table = {
        "core": "",
        "runtime": "[runtime]",
        "ml": "[ml]",
        "dev": "[dev]",
        "eval": "[eval]",
        "validate": "[validate]",
        "fhir": "[fhir]",
        "all": "[runtime,ml,dev,eval,validate,fhir]",
    }
    return table.get(skill, "")
