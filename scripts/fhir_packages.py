#!/usr/bin/env python
"""Prefetch FHIR Implementation Guide packages into a local cache.

Reads ``config/fhir_target.yaml`` to determine the package id and version to
prefetch. Packages are downloaded from ``https://packages.fhir.org`` and
extracted under ``.fhir/packages``.

Example::

    python scripts/fhir_packages.py --config config/fhir_target.yaml
"""
from __future__ import annotations

import argparse
import io
import pathlib
import tarfile
from typing import Tuple

import requests
import yaml


def _load_target(cfg_path: pathlib.Path) -> Tuple[str, str]:
    with cfg_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg["package_id"], cfg["package_version"]


def _fetch_package(pkg_id: str, pkg_ver: str, dest: pathlib.Path) -> pathlib.Path:
    dest.mkdir(parents=True, exist_ok=True)
    pkg_dir = dest / f"{pkg_id}#{pkg_ver}"
    if pkg_dir.exists():
        print(f"[fhir-packages] cache hit: {pkg_dir}")
        return pkg_dir

    url = f"https://packages.fhir.org/{pkg_id}/{pkg_ver}"
    print(f"[fhir-packages] downloading {url}")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    with tarfile.open(fileobj=io.BytesIO(resp.content), mode="r:gz") as tar:
        tar.extractall(pkg_dir)

    print(f"[fhir-packages] extracted to {pkg_dir}")
    return pkg_dir


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default="config/fhir_target.yaml",
                    help="Path to FHIR target configuration")
    ap.add_argument("--cache", default=".fhir/packages",
                    help="Destination cache directory")
    args = ap.parse_args()

    cfg_path = pathlib.Path(args.config)
    cache_dir = pathlib.Path(args.cache)

    pkg_id, pkg_ver = _load_target(cfg_path)
    _fetch_package(pkg_id, pkg_ver, cache_dir)


if __name__ == "__main__":
    main()
