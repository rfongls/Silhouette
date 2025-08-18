#!/usr/bin/env python
"""Simple repository scanner for secrets and license compliance."""
import argparse
import json
import pathlib
import re
import sys
from typing import Dict, List
from .redaction import Redactor

DEFAULT_OUT = pathlib.Path("artifacts/security_report.json")

SPDX_LICENSE_RE = re.compile(
    r"(?i)spdx[-\s]*license[-\s]*identifier:\s*([A-Za-z0-9\-\.\+]+)"
)

# Default allow list of permissive licenses.  Deny list may be provided via CLI.
SPDX_WHITELIST = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause"}
SPDX_DENYLIST: set[str] = {"GPL-3.0", "AGPL-3.0", "MPL-2.0"}


def _iter_files(root: pathlib.Path) -> List[pathlib.Path]:
    """Yield reasonably-sized files under ``root`` ignoring ``.git``."""
    for p in root.rglob("*"):
        if p.is_file() and ".git" not in p.parts and p.stat().st_size <= 1_000_000:
            yield p

def scan_path(root: pathlib.Path) -> Dict[str, List[Dict[str, str]]]:
    """Scan ``root`` and return findings grouped with severity counts."""

    red = Redactor()
    findings: List[Dict[str, str]] = []

    for f in _iter_files(root):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        # Secrets/PII patterns
        for pat, _ in red.patterns:
            for m in pat.finditer(text):
                snippet = text[m.start() : m.end()][:120]
                findings.append(
                    {
                        "path": str(f),
                        "pattern": pat.pattern,
                        "match": snippet,
                        "category": "pii",
                        "severity": "medium",
                    }
                )

        # License scanning
        m = SPDX_LICENSE_RE.search(text)
        if m:
            lic = m.group(1)
            if lic in SPDX_WHITELIST:
                findings.append(
                    {
                        "path": str(f),
                        "category": "license_whitelisted",
                        "severity": "low",
                        "license": lic,
                    }
                )
            elif lic in SPDX_DENYLIST:
                findings.append(
                    {
                        "path": str(f),
                        "category": "license_blocked",
                        "severity": "high",
                        "license": lic,
                    }
                )
            else:
                findings.append(
                    {
                        "path": str(f),
                        "category": "license_unknown",
                        "severity": "medium",
                        "license": lic,
                    }
                )
        else:
            findings.append(
                {
                    "path": str(f),
                    "category": "non_licensed",
                    "severity": "low",
                }
            )

    counts = {
        "low": sum(1 for f in findings if f.get("severity") == "low"),
        "medium": sum(1 for f in findings if f.get("severity") == "medium"),
        "high": sum(1 for f in findings if f.get("severity") == "high"),
    }

    return {
        "findings": findings,
        "counts": counts,
        "license_whitelist": sorted(SPDX_WHITELIST),
        "license_denylist": sorted(SPDX_DENYLIST),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default=".", help="root path to scan")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--max_low", type=int, default=1000)
    ap.add_argument("--max_medium", type=int, default=100)
    ap.add_argument("--max_high", type=int, default=0)
    ap.add_argument(
        "--license_whitelist",
        default="MIT,Apache-2.0,BSD-2-Clause,BSD-3-Clause",
        help="comma-separated SPDX IDs allowed",
    )
    ap.add_argument(
        "--license_denylist",
        default="",
        help="comma-separated SPDX IDs that are blocked",
    )
    args = ap.parse_args()

    if args.license_whitelist:
        SPDX_WHITELIST.clear()
        SPDX_WHITELIST.update({w.strip() for w in args.license_whitelist.split(",") if w.strip()})
    if args.license_denylist:
        SPDX_DENYLIST.clear()
        SPDX_DENYLIST.update({w.strip() for w in args.license_denylist.split(",") if w.strip()})

    root = pathlib.Path(args.path)
    report = scan_path(root)
    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        f"Wrote security report with {len(report['findings'])} findings -> {args.out}"
    )
    if (
        report["counts"]["high"] > args.max_high
        or report["counts"]["medium"] > args.max_medium
        or report["counts"]["low"] > args.max_low
    ):
        sys.exit(1)


if __name__ == "__main__":
    main()
