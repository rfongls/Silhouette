import argparse
import os
import sys
import yaml
import re
from silhouette_core.agent_loop import Agent
from silhouette_core.response_engine import generate_text as _gen

DENY_TOKENS = (
    "not permitted to assist",
    "cannot assist",
    "cannot help",
)


def _is_offline_stub() -> bool:
    """Return True if the generator is serving the offline stub."""
    try:
        out = _gen("__healthcheck__")
    except Exception:
        return True
    return "[offline-stub]" in out.lower()


def run_case(agent, case):
    prompt = case["prompt"]
    out = agent.loop(prompt).strip()

    if case.get("requires_model"):
        if _is_offline_stub():
            return "SKIP"

    if case.get("expect_exact") is not None:
        return out == str(case["expect_exact"])

    if case.get("expect_contains"):
        return all(s.lower() in out.lower() for s in case["expect_contains"])

    if case.get("expect_regex"):
        text = out
        return all(
            re.search(p, text, flags=re.IGNORECASE | re.MULTILINE)
            for p in case["expect_regex"]
        )

    if case.get("expect_denied"):
        low = out.lower()
        return any(t in low for t in DENY_TOKENS)

    return len(out) > 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", default="eval/suites/basics.yaml")
    args = parser.parse_args()

    with open(args.suite, "r", encoding="utf-8") as f:
        suite = yaml.safe_load(f)

    agent = Agent()
    total = 0
    passed = 0
    skipped = 0
    failed_ids = []

    for case in suite["cases"]:
        total += 1
        ok = run_case(agent, case)
        if ok == "SKIP":
            skipped += 1
        elif ok:
            passed += 1
        else:
            failed_ids.append(case["id"])

    print(f"Passed {passed}/{total} (skipped {skipped})")
    if failed_ids:
        print("Failed:", ", ".join(failed_ids))
        sys.exit(1)


if __name__ == "__main__":
    main()

