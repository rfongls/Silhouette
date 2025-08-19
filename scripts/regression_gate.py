#!/usr/bin/env python3
import argparse, json, sys, pathlib, statistics, yaml

def load_json(p):
    path = pathlib.Path(p)
    return json.loads(path.read_text()) if path.exists() else {}

def load_yaml(p):
    return yaml.safe_load(pathlib.Path(p).read_text())

def pct(n, d):
    return 0.0 if d == 0 else n / d

def within_tolerance(value, cap, tol_pct):
    return value <= cap * (1 + tol_pct / 100.0)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default="artifacts/scoreboard/latest.json", help="aggregated eval+latency JSON")
    ap.add_argument("--previous", default="artifacts/scoreboard/previous.json", help="previous snapshot for trend")
    ap.add_argument("--gates", default="config/gates.yaml")
    ap.add_argument("--lanes", default="config/lanes.yaml")
    args = ap.parse_args()

    rep = load_json(args.report)
    prev = load_json(args.previous)
    gates = load_yaml(args.gates)
    lanes_cfg = load_yaml(args.lanes)["lanes"]

    quarantine_tests = set(gates.get("quarantine", {}).get("tests", []))
    quarantine_lanes = set(gates.get("quarantine", {}).get("lanes", []))

    failures = []
    summary = {"lanes": {}, "latency": {}, "notes": []}

    lanes = rep.get("lanes", {})
    for lane in lanes_cfg:
        if lane in quarantine_lanes:
            summary["lanes"][lane] = {"status": "skipped", "reason": "quarantined"}
            continue
        lane_rep = lanes.get(lane, {"passed": 0, "total": 0})
        passed = lane_rep.get("passed", 0)
        total = lane_rep.get("total", 0)
        rate = pct(passed, total)
        min_rate = gates["lanes"].get(lane, {}).get("min_pass_rate", 0.0)
        ok = rate >= min_rate
        summary["lanes"][lane] = {
            "passed": passed,
            "total": total,
            "rate": rate,
            "min_rate": min_rate,
            "status": "ok" if ok else "fail",
        }
        if not ok:
            failures.append(f"Lane '{lane}' pass rate {rate:.2%} < {min_rate:.2%}")

        if prev:
            prev_lane = prev.get("lanes", {}).get(lane, {})
            prev_rate = pct(prev_lane.get("passed", 0), prev_lane.get("total", 0))
            drop = (prev_rate - rate) * 100
            if prev_lane and drop > gates["regression"]["fail_on_drop_pct"]:
                failures.append(
                    f"Lane '{lane}' regressed by {drop:.1f}% (> {gates['regression']['fail_on_drop_pct']}%)"
                )
                summary["lanes"][lane]["regressed_pct"] = drop

    lat = rep.get("latency", {})
    for key, spec in gates.get("latency", {}).items():
        val = lat.get(key, None)
        if val is None:
            failures.append(f"Latency metric '{key}' missing in report")
            summary["latency"][key] = {"status": "missing"}
            continue
        cap = spec["max"]
        tol = spec.get("tolerance_pct", 0)
        ok = within_tolerance(val, cap, tol)
        summary["latency"][key] = {
            "value": val,
            "cap": cap,
            "tolerance_pct": tol,
            "status": "ok" if ok else "fail",
        }
        if not ok:
            failures.append(f"Latency '{key}' {val:.2f}s exceeds {cap:.2f}s (+{tol}% allowed)")

    out_dir = pathlib.Path("artifacts/gates")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "gate_summary.json").write_text(json.dumps(summary, indent=2))

    if failures:
        (out_dir / "gate_failures.txt").write_text("\n".join(failures))
        print("REGRESSION GATES FAILED:\n- " + "\n- ".join(failures))
        sys.exit(1)
    else:
        print("All regression & latency gates passed.")
        sys.exit(0)

if __name__ == "__main__":
    main()
