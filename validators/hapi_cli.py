from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Iterable

import yaml

JAR_PATH = Path("validators/validator_cli.jar")


class HapiValidationError(RuntimeError):
    """Raised when the HAPI validator reports an error."""


def run(files: Iterable[str]) -> None:
    """Validate FHIR resources using the HAPI validator CLI.

    Args:
        files: Iterable of file paths containing FHIR resources (JSON/NDJSON).

    Raises:
        RuntimeError: If Java is not configured or validation fails.
    """

    java_home = os.environ.get("JAVA_HOME")
    if not java_home:
        raise RuntimeError("JAVA_HOME not set; install Java to enable HAPI validation")
    java = Path(java_home) / "bin" / "java"
    if not java.exists():
        raise RuntimeError(f"java executable not found under {java_home}")
    if not JAR_PATH.exists():
        raise RuntimeError(f"HAPI validator CLI jar not found at {JAR_PATH}")

    cfg = yaml.safe_load(Path("config/fhir_target.yaml").read_text(encoding="utf-8"))
    package_id = cfg.get("package_id", "hl7.fhir.us.core")
    package_version = cfg.get("package_version")
    ig_arg = f"{package_id}#{package_version}" if package_version else package_id

    cmd = [
        str(java),
        "-jar",
        str(JAR_PATH),
        "-ig",
        ig_arg,
        "-package-cache",
        ".fhir/packages",
    ]
    cmd.extend(str(Path(f)) for f in files)

    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        raise HapiValidationError(str(e)) from e
