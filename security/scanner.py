#!/usr/bin/env python
"""Simple repo scanner for security findings."""
import argparse
import json
import pathlib
import re
import sys
from typing import List
from .redaction import Redactor

DEFAULT_OUT = pathlib.Path("artifacts/security_report.json")

SPDX_LICENSE_RE = re.compile(r"(?i)spdx[-\s]*license[-\s]*identifier:\s*([A-Za-z0-9\-\.\+]+)")
SPDX_WHITELIST = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause"}


def _iter_files(root: pathlib.Path) -> List[pathlib.Path]:
    for p in root.rglob("*"):
        if p.is_file() and ".git" not in p.parts and p.stat().st_size <= 1_000_000:
            yield p


def scan_path(root: pathlib.Path) -> dict:
    red = Redactor()
    findings = []
    for f in _iter_files(root):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pat, _ in red.patterns:
            for m in pat.finditer(text):
                snippet = text[m.start():m.end()][:120]
                findings.append(
                    {
                        "path": str(f),
                        "pattern": pat.pattern,
                        "match": snippet,
                        "category": "pii",
                        "severity": "medium",
                    }
                )
        for m in SPDX_LICENSE_RE.finditer(text):
            lic = m.group(1)
            if lic not in SPDX_WHITELIST:
                findings.append(
                    {
                        "path": str(f),
                        "category": "license",
                        "severity": "high",
                        "license": lic,
                    }
                )
    n_medium = sum(1 for f in findings if f.get("severity") == "medium")
    n_high = sum(1 for f in findings if f.get("severity") == "high")
    return {
        "findings": findings,
        "counts": {"medium": n_medium, "high": n_high},
        "license_whitelist": sorted(SPDX_WHITELIST),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default=".", help="root path to scan")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--max_medium", type=int, default=1000)
    ap.add_argument("--max_high", type=int, default=0)
    ap.add_argument("--whitelist", help="comma-separated SPDX license IDs")
    args = ap.parse_args()

    if args.whitelist:
        SPDX_WHITELIST.clear()
        SPDX_WHITELIST.update({w.strip() for w in args.whitelist.split(",") if w.strip()})

    root = pathlib.Path(args.path)
    report = scan_path(root)
    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        f"Wrote security report with {len(report['findings'])} findings -> {args.out}"
    )
    if report["counts"]["high"] > args.max_high or report["counts"]["medium"] > args.max_medium:
        sys.exit(1)


if __name__ == "__main__":
    main()
