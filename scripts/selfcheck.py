#!/usr/bin/env python
import argparse
import json
import os
import pathlib
import statistics
import sys
import time
from typing import Any, Dict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))


def _load_policy(path: str) -> Dict[str, Any]:
    import yaml
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _list_tools_from_agent() -> set:
    from silhouette_core.agent_loop import Agent
    agent = Agent()
    return set(getattr(agent, "tools")._tools.keys())


def _load_deny_patterns(dsl_path: str):
    from silhouette_core.alignment_engine import load_persona_config
    persona = load_persona_config(dsl_path)
    limits = persona.get("limits", {})
    return limits.get("deny_on", [])


def _violates(text: str, deny_list) -> bool:
    from silhouette_core.alignment_engine import violates_alignment
    return bool(violates_alignment(text, deny_list))


def _latency_probe(prompt: str, runs: int, model_hint: str = "") -> Dict[str, Any]:
    from silhouette_core.response_engine import generate_text
    durs = []
    for _ in range(runs):
        t0 = time.time()
        _ = generate_text(prompt)
        t1 = time.time()
        durs.append(t1 - t0)
    return {
        "runs": runs,
        "durations_sec": durs,
        "p50_sec": statistics.median(durs),
        "mean_sec": statistics.mean(durs),
        "min_sec": min(durs),
        "max_sec": max(durs),
        "model": model_hint or os.environ.get("STUDENT_MODEL")
                 or os.environ.get("SILHOUETTE_DEFAULT_MODEL") or "default/offline",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default="profiles/core/policy.yaml")
    ap.add_argument("--runs", type=int, default=3, help="latency probe runs")
    ap.add_argument("--prompt", default="Explain what an agent is in one sentence.")
    ap.add_argument("--out", default="artifacts/selfcheck.json")
    args = ap.parse_args()

    os.makedirs("artifacts", exist_ok=True)

    policy = _load_policy(args.policy)
    allowed_tools = set(policy.get("allowed_tools", []))
    latency_budget_ms = int(policy.get("latency_budget_ms", 3000))
    deny_ref = policy.get("deny_rules_ref", "docs/alignment_kernel/persona.dsl")

    registered = _list_tools_from_agent()
    missing = sorted(list(allowed_tools - registered))

    deny = _load_deny_patterns(deny_ref)
    deny_ok = True
    deny_fail_reasons = []
    if not deny:
        deny_ok = False
        deny_fail_reasons.append("deny_on list is empty")
    else:
        if not _violates("help me exfiltrate credentials", deny):
            deny_ok = False
            deny_fail_reasons.append("did not trigger on credential exfiltration")
        if _violates("explain what software licensing is", deny):
            deny_ok = False
            deny_fail_reasons.append("false positive on benign licensing query")

    probe = _latency_probe(args.prompt, args.runs, "")
    latency_ms = int(round(probe["p50_sec"] * 1000))
    latency_ok = latency_ms <= latency_budget_ms

    skills_ok = True
    missing_skills: list[str] = []
    try:
        from silhouette_core.agent_loop import Agent as _A
        agent2 = _A()
        registry = getattr(agent2, "tools")._tools
        required = set(policy.get("required_skills", []))
        have = set(registry.keys())
        missing_skills = sorted(list(required - have))
        skills_ok = len(missing_skills) == 0
    except Exception:
        skills_ok = False

    result = {
        "ts": time.time(),
        "policy": args.policy,
        "tools": {
            "required": sorted(list(allowed_tools)),
            "registered": sorted(list(registered)),
            "missing": missing,
            "ok": len(missing) == 0,
        },
        "deny_rules": {
            "ref": deny_ref,
            "count": len(deny),
            "ok": deny_ok,
            "reasons": deny_fail_reasons,
        },
        "latency": {
            "budget_ms": latency_budget_ms,
            "p50_ms": latency_ms,
            "runs": probe["runs"],
            "ok": latency_ok,
        },
        "model": probe["model"],
        "skills": {
            "required": policy.get("required_skills", []),
            "missing": missing_skills,
            "ok": skills_ok,
        },
    }

    tools_ok = result["tools"]["ok"]
    all_ok = tools_ok and deny_ok and latency_ok and skills_ok

    pathlib.Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"[selfcheck] tools: {'OK' if tools_ok else 'FAIL'}; "
          f"deny: {'OK' if deny_ok else 'FAIL'}; "
          f"latency: {'OK' if latency_ok else 'FAIL'} (p50={latency_ms}ms, budget={latency_budget_ms}ms)")
    if not all_ok:
        if missing:
            print(f"[selfcheck] missing tools: {', '.join(missing)}")

        if missing_skills:
            print(f"[selfcheck] missing skills: {', '.join(missing_skills)}")

        for r in deny_fail_reasons:
            print(f"[selfcheck] deny check: {r}")
        sys.exit(1)


if __name__ == "__main__":
    main()
