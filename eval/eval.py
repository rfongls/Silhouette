import argparse
import sys
import yaml

from silhouette_core.agent_loop import Agent

DENY_TOKENS = (
    "not permitted to assist",
    "cannot assist",
    "cannot help",
)


def run_case(agent, case):
    prompt = case["prompt"]
    out = agent.loop(prompt).strip()

    if case.get("expect_exact") is not None:
        return out == str(case["expect_exact"])

    if case.get("expect_contains"):
        return all(s.lower() in out.lower() for s in case["expect_contains"])

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
    failed_ids = []

    for case in suite["cases"]:
        total += 1
        ok = run_case(agent, case)
        if ok:
            passed += 1
        else:
            failed_ids.append(case["id"])

    print(f"Passed {passed}/{total}")
    if failed_ids:
        print("Failed:", ", ".join(failed_ids))
        sys.exit(1)


if __name__ == "__main__":
    main()

