from __future__ import annotations
from pathlib import Path
from silhouette_core.drift_detector import load_entries, tone_distribution, detect_drift


def test_drift_detector_smoke(tmp_path: Path):
    p = tmp_path / "log.jsonl"
    p.write_text('{"content":"hello"}\n{"content":"great!"}\n', encoding="utf-8")
    entries = load_entries(p)
    dist = tone_distribution(entries)
    assert sum(dist.values()) > 0
    drift = detect_drift({"neutral": 1.0}, dist, threshold=0.0)
    assert isinstance(drift, dict)
