#!/usr/bin/env python
import json
import os
import pathlib
import statistics
import sys
import time


def generate_text(prompt: str) -> str:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from silhouette_core.response_engine import generate_text as _gen
    return _gen(prompt)


def main():
    os.makedirs("artifacts", exist_ok=True)
    prompt = os.environ.get("LAT_PROMPT", "Explain what an agent is in one sentence.")
    runs = int(os.environ.get("LAT_RUNS", "5"))
    sleep_s = float(os.environ.get("LAT_SLEEP", "0.0"))

    durs = []
    for _ in range(runs):
        t0 = time.time()
        _ = generate_text(prompt)
        t1 = time.time()
        durs.append(t1 - t0)
        if sleep_s > 0:
            time.sleep(sleep_s)

    result = {
        "prompt": prompt,
        "runs": runs,
        "durations_sec": durs,
        "p50_sec": statistics.median(durs),
        "mean_sec": statistics.mean(durs),
        "min_sec": min(durs),
        "max_sec": max(durs),
        "model": os.environ.get("STUDENT_MODEL")
        or os.environ.get("SILHOUETTE_DEFAULT_MODEL")
        or "default/offline",
        "ts": time.time(),
    }
    pathlib.Path("artifacts/latency.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(
        f"Latency p50={result['p50_sec']:.3f}s mean={result['mean_sec']:.3f}s (runs={runs}) using model='{result['model']}'"
    )


if __name__ == "__main__":
    main()
