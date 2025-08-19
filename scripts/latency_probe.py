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

    p50 = statistics.median(durs)
    mean = statistics.mean(durs)
    summary = {"p50": p50, "mean": mean, "device": "cpu"}
    if os.environ.get("SILHOUETTE_EDGE") == "1":
        summary["edge_mode"] = True
        print(f"[EDGE MODE] p50={p50:.2f}s mean={mean:.2f}s")
    else:
        print(f"p50={p50:.2f}s mean={mean:.2f}s")
    out = pathlib.Path("artifacts/latency/latency.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
