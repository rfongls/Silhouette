import argparse
import json
from collections import Counter
from pathlib import Path

from .tone_parser import score_tone

CONFIG_PATH = Path("config/drift.yml")


def load_config(path: Path = CONFIG_PATH) -> dict:
    data: dict[str, float] = {}
    if not path.is_file():
        return data
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, val = (x.strip() for x in line.split(":", 1))
            try:
                data[key] = float(val)
            except ValueError:
                data[key] = val
    return data


def load_entries(path: Path, limit: int = 100) -> list[dict]:
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
    entries = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def tone_distribution(entries: list[dict]) -> dict:
    counts = Counter()
    for e in entries:
        tone = score_tone(e.get("content", ""))
        counts[tone] += 1
    total = sum(counts.values())
    if not total:
        return {}
    return {k: v / total for k, v in counts.items()}


def detect_drift(baseline: dict, recent: dict, threshold: float) -> dict:
    drift = {}
    all_keys = set(baseline) | set(recent)
    for k in all_keys:
        diff = recent.get(k, 0.0) - baseline.get(k, 0.0)
        if abs(diff) >= threshold:
            drift[k] = diff
    return drift


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Detect tone drift")
    parser.add_argument("--baseline", default="memory_baseline.jsonl")
    parser.add_argument("--current", default="memory.jsonl")
    args = parser.parse_args(argv)

    cfg = load_config()
    thresh = float(cfg.get("tone_threshold", 0.2))
    base_entries = load_entries(Path(args.baseline))
    cur_entries = load_entries(Path(args.current))
    base_dist = tone_distribution(base_entries)
    cur_dist = tone_distribution(cur_entries)
    drift = detect_drift(base_dist, cur_dist, thresh)
    if drift:
        print("Tone drift detected:")
        for tone, delta in drift.items():
            print(f"  {tone}: {delta:+.2f}")
    else:
        print("No tone drift detected.")


if __name__ == "__main__":
    main()
