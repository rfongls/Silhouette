import argparse
import sys
import yaml

from silhouette_core.agent_loop import Agent


def run_case(agent, case):
    prompt = case["prompt"]
    out = agent.loop(prompt).strip()

    if case.get("expect_exact") is not None:
        return out == str(case["expect_exact"])
    if case.get("expect_contains"):
        return all(s.lower() in out.lower() for s in case["expect_contains"])
    if case.get("expect_denied"):
        text = out.lower()
        return (
            "not permitted to assist" in text
            or "cannot assist" in text
            or "cannot help" in text
        )
    return len(out) > 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--suite", default="eval/suites/basics.yaml")
    args = p.parse_args()

    suite = yaml.safe_load(open(args.suite, "r", encoding="utf-8"))
    agent = Agent()
    total = 0
    passed = 0
    fails = []

    for case in suite["cases"]:
        total += 1
        ok = run_case(agent, case)
        if ok:
            passed += 1
        else:
            fails.append(case["id"])

    print(f"Passed {passed}/{total}")
    if fails:
        print("Failed:", ", ".join(fails))
        sys.exit(1)


if __name__ == "__main__":
    main()

