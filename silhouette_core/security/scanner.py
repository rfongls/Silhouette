from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Iterable, List, Dict

# Regex patterns for common secrets
SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ASIA[0-9A-Z]{16}"),
    re.compile(r"aws_secret_access_key", re.IGNORECASE),
    re.compile(r"-----BEGIN (?:RSA|DSA|EC|OPENSSH) PRIVATE KEY-----"),
    re.compile(r"secret_key\s*=\s*['\"][^'\"]+['\"]", re.IGNORECASE),
]

ALLOWLIST_PATTERNS = [re.compile(p) for p in ["DUMMY_.*", "EXAMPLE_.*"]]


def _entropy(s: str) -> float:
    probs = [s.count(c) / len(s) for c in set(s)]
    return -sum(p * math.log2(p) for p in probs)


def scan_text(text: str, path: str) -> List[Dict[str, object]]:
    findings: List[Dict[str, object]] = []
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


def scan_paths(paths: Iterable[Path]) -> List[Dict[str, object]]:
    results: List[Dict[str, object]] = []
    for p in paths:
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        results.extend(scan_text(text, str(p)))
    return results
