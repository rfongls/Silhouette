#!/usr/bin/env python
"""Simple repo scanner for security findings."""
import argparse
import json
import pathlib
from typing import List
from .redaction import Redactor

DEFAULT_OUT = pathlib.Path("artifacts/security_report.json")


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
                findings.append({"path": str(f), "pattern": pat.pattern, "match": snippet})
    return {"findings": findings, "total": len(findings)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default=".", help="root path to scan")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    root = pathlib.Path(args.path)
    report = scan_path(root)
    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote security report with {report['total']} findings -> {args.out}")


if __name__ == "__main__":
    main()
