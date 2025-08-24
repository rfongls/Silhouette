from __future__ import annotations

import argparse
import json
import math
import re
from collections.abc import Iterable
from pathlib import Path

# Regex patterns for common secrets
SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ASIA[0-9A-Z]{16}"),
    re.compile(r"aws_secret_access_key", re.IGNORECASE),
    re.compile(r"-----BEGIN (?:RSA|DSA|EC|OPENSSH) PRIVATE KEY-----"),
    re.compile(r"secret_key\s*=\s*['\"][^'\"]+['\"]", re.IGNORECASE),
]

ALLOWLIST_PATTERNS = [re.compile(p) for p in ["DUMMY_.*", "EXAMPLE_.*"]]

SPDX_LICENSE_RE = re.compile(r"(?i)spdx[-\s]*license[-\s]*identifier:\s*([A-Za-z0-9\-\.\+]+)")
SPDX_WHITELIST = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause"}
SPDX_DENYLIST: set[str] = {"GPL-3.0", "AGPL-3.0", "MPL-2.0"}

DEFAULT_OUT = Path("artifacts/security_report.json")


def _entropy(s: str) -> float:
    probs = [s.count(c) / len(s) for c in set(s)]
    return -sum(p * math.log2(p) for p in probs)


def scan_text(text: str, path: str) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for pat in SECRET_PATTERNS:
            if pat.search(line) and not any(a.search(line) for a in ALLOWLIST_PATTERNS):
                findings.append({"path": path, "line": lineno, "match": line.strip(), "reason": pat.pattern})
        for token in re.findall(r"[A-Za-z0-9+/=]{20,}|[A-Fa-f0-9]{20,}", line):
            if any(a.search(token) for a in ALLOWLIST_PATTERNS):
                continue
            if _entropy(token) >= 3.5:
                findings.append({"path": path, "line": lineno, "match": token, "reason": "entropy"})
    return findings


def scan_paths(paths: Iterable[Path]) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for p in paths:
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        results.extend(scan_text(text, str(p)))
    return results


def _iter_files(root: Path) -> list[Path]:
    for p in root.rglob("*"):
        if p.is_file() and ".git" not in p.parts and p.stat().st_size <= 1_000_000:
            yield p


def scan_path(root: Path) -> dict[str, list[dict[str, str]]]:
    findings: list[dict[str, str]] = []

    for f in _iter_files(root):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        m = SPDX_LICENSE_RE.search(text)
        if m:
            lic = m.group(1)
            if lic in SPDX_WHITELIST:
                findings.append({"path": str(f), "category": "license_whitelisted", "severity": "low", "license": lic})
            elif lic in SPDX_DENYLIST:
                findings.append({"path": str(f), "category": "license_blocked", "severity": "high", "license": lic})
            else:
                findings.append({"path": str(f), "category": "license_unknown", "severity": "medium", "license": lic})
        else:
            findings.append({"path": str(f), "category": "non_licensed", "severity": "low"})

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
    ap.add_argument("--license_whitelist", default="MIT,Apache-2.0,BSD-2-Clause,BSD-3-Clause")
    ap.add_argument("--license_denylist", default="", help="comma-separated SPDX IDs that are blocked")
    args = ap.parse_args()

    if args.license_whitelist:
        SPDX_WHITELIST.clear()
        SPDX_WHITELIST.update({w.strip() for w in args.license_whitelist.split(",") if w.strip()})
    if args.license_denylist:
        SPDX_DENYLIST.clear()
        SPDX_DENYLIST.update({w.strip() for w in args.license_denylist.split(",") if w.strip()})

    root = Path(args.path)
    report = scan_path(root)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote security report with {len(report['findings'])} findings -> {args.out}")
    if (
        report["counts"]["high"] > args.max_high
        or report["counts"]["medium"] > args.max_medium
        or report["counts"]["low"] > args.max_low
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
