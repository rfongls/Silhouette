#!/usr/bin/env python
"""
Aggregate artifacts and render a static HTML scoreboard:
- artifacts/selfcheck.json
- artifacts/eval_report.json
- artifacts/latency.json
- artifacts/build_eval_report.json (runtime evals; multiple files allowed)
Writes to: artifacts/scoreboard/index.html
Offline-friendly; tolerates missing files.
"""
import glob
import html
import json
import os
import pathlib
import time
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from security.scanner import SPDX_WHITELIST


def aggregate_json(runtime_reports, latency):
    """Build a minimal JSON summary for regression gates."""
    lanes = {}
    for rep in runtime_reports or []:
        if not rep:
            continue
        lane = rep.get("lane") or rep.get("suite")
        if not lane:
            continue
        lanes[lane] = {
            "passed": int(rep.get("passed", 0)),
            "total": int(rep.get("total", 0)),
        }
    lat = {}
    if isinstance(latency, dict):
        if latency.get("selfcheck_p50") is not None:
            lat["selfcheck_p50"] = latency.get("selfcheck_p50")
        if latency.get("short_answer_p50") is not None:
            lat["short_answer_p50"] = latency.get("short_answer_p50")
    return {"lanes": lanes, "latency": lat}

ART_DIR = pathlib.Path("artifacts")
OUT_DIR = ART_DIR / "scoreboard"
OUT_PATH = OUT_DIR / "index.html"

def _load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def _row(k, v):
    return f"<tr><td class='k'>{html.escape(str(k))}</td><td>{html.escape(str(v))}</td></tr>"

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    selfcheck = _load_json(ART_DIR / "selfcheck.json")
    eval_rep = _load_json(ART_DIR / "eval_report.json")
    latency = _load_json(ART_DIR / "latency.json")
    security_rep = _load_json(ART_DIR / "security_report.json")
    lint_py = _load_json(ART_DIR / "lint_python.json")
    lint_js = _load_json(ART_DIR / "lint_js.json")
    lint_cpp = _load_json(ART_DIR / "lint_cpp.json")

    runtime_reports = []
    for p in glob.glob(str(ART_DIR / "*.build_eval_report.json")) + glob.glob(
        str(ART_DIR / "build_eval_report.json")
    ):
        runtime_reports.append(_load_json(pathlib.Path(p)))

    parts = []
    parts.append("<!doctype html><meta charset='utf-8'><title>Silhouette Scoreboard — Cross-Language Agent Capability</title>")
    parts.append(
        """
<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Arial,sans-serif;margin:24px;color:#111}
h1{margin:0 0 8px} .ts{color:#666;font-size:12px;margin-bottom:16px}
.card{border:1px solid #e5e7eb;border-radius:12px;padding:16px;margin:12px 0;box-shadow:0 1px 3px #0001}
h2{margin:0 0 12px;font-size:18px}
table{border-collapse:collapse;width:100%} td,th{padding:6px 8px;border-bottom:1px solid #eee}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;margin-left:6px}
.ok{background:#e6f4ea;color:#137333} .fail{background:#fde8e8;color:#b91c1c} .skip{background:#eef2ff;color:#4338ca}
.k{width:220px;color:#555}
small{color:#666}
</style>
"""
    )
    parts.append("<h1>Silhouette Scoreboard — Cross-Language Agent Capability</h1>")
    parts.append(f"<div class='ts'>Generated {time.strftime('%Y-%m-%d %H:%M:%S')}</div>")

    parts.append("<div class='card'><h2>Self-check</h2>")
    if selfcheck:
        ok = all([
            selfcheck.get("tools", {}).get("ok"),
            selfcheck.get("deny_rules", {}).get("ok"),
            selfcheck.get("latency", {}).get("ok"),
            selfcheck.get("skills", {}).get("ok", True),
        ])
        badge = "<span class='badge ok'>OK</span>" if ok else "<span class='badge fail'>FAIL</span>"
        parts.append(f"<div>Overall: {badge}</div><br/>")
        parts.append("<table>")
        parts.append(_row("Tools OK", selfcheck.get("tools", {}).get("ok")))
        parts.append(_row("Missing Tools", ", ".join(selfcheck.get("tools", {}).get("missing", []))))
        parts.append(_row("Deny Rules OK", selfcheck.get("deny_rules", {}).get("ok")))
        parts.append(_row("Latency p50 (ms)", selfcheck.get("latency", {}).get("p50_ms")))
        parts.append(_row("Latency Budget (ms)", selfcheck.get("latency", {}).get("budget_ms")))
        parts.append(_row("Skills OK", selfcheck.get("skills", {}).get("ok")))
        parts.append(_row("Missing Skills", ", ".join(selfcheck.get("skills", {}).get("missing", []))))
        parts.append("</table>")
    else:
        parts.append("<small>No selfcheck.json found.</small>")
    parts.append("</div>")

    parts.append("<div class='card'><h2>Agent Eval</h2>")
    if eval_rep:
        rc = eval_rep.get("returncode", 0)
        badge = "<span class='badge ok'>OK</span>" if rc == 0 else "<span class='badge fail'>FAIL</span>"
        parts.append(f"<div>Run: {badge}</div><br/>")
        parts.append("<table>")
        parts.append(_row("Suite", eval_rep.get("suite")))
        parts.append(_row("Return code", rc))
        parts.append(_row("Passed line", eval_rep.get("passed")))
        parts.append(_row("Model", eval_rep.get("student_model", "")))
        parts.append("</table>")
    else:
        parts.append("<small>No eval_report.json found.</small>")
    parts.append("</div>")

    parts.append("<div class='card'><h2>Latency</h2>")
    if latency:
        parts.append("<table>")
        parts.append(_row("Model", latency.get("model")))
        parts.append(_row("Prompt", latency.get("prompt")))
        parts.append(_row("p50 (s)", latency.get("p50_sec")))
        parts.append(_row("mean (s)", latency.get("mean_sec")))
        parts.append("</table>")
    else:
        parts.append("<small>No latency.json found.</small>")
    parts.append("</div>")

    parts.append("<div class='card'><h2>Lint</h2>")
    if lint_py or lint_js or lint_cpp:
        parts.append("<table>")
        if lint_py:
            py_badge = (
                "<span class='badge ok'>OK</span>" if lint_py.get("ok") else "<span class='badge fail'>FAIL</span>"
            )
            parts.append(_row("Python", f"{lint_py.get('issues',0)} issues {py_badge}"))
        if lint_js:
            js_badge = (
                "<span class='badge ok'>OK</span>" if lint_js.get("ok") else "<span class='badge fail'>FAIL</span>"
            )
            parts.append(_row("Web/JS", f"{lint_js.get('issues',0)} issues {js_badge}"))

        if lint_cpp:
            cpp_badge = (
                "<span class='badge ok'>OK</span>" if lint_cpp.get("ok") else "<span class='badge fail'>FAIL</span>"
            )
            parts.append(_row("C++", f"{lint_cpp.get('issues',0)} issues {cpp_badge}"))
        parts.append("</table>")
    else:
        parts.append("<small>No lint reports found.</small>")
    parts.append("</div>")

    parts.append("<div class='card'><h2>Runtime Suites</h2>")
    if runtime_reports:
        for rep in runtime_reports:
            if not rep:
                continue
            skipped = bool(rep.get("skipped"))
            badge = (
                "<span class='badge skip'>SKIP</span>"
                if skipped
                else (
                    "<span class='badge ok'>OK</span>"
                    if rep.get("failed_ids") in ([], None)
                    else "<span class='badge fail'>FAIL</span>"
                )
            )
            parts.append(
                f"<h3 style='margin-top:8px'>{html.escape(rep.get('suite', '(unknown)'))} {badge}</h3>"
            )
            if skipped:
                parts.append(
                    f"<small>Reason: {html.escape(rep.get('reason', ''))}</small>"
                )
            else:
                parts.append("<table>")
                parts.append(_row("Passed", rep.get("passed")))
                parts.append(_row("Total", rep.get("total")))
                parts.append(_row("Failed IDs", ", ".join(rep.get("failed_ids", []))))
                parts.append("</table>")
    else:
        parts.append("<small>No runtime build reports found.</small>")
    parts.append("</div>")

    parts.append("<div class='card'><h2>Security</h2>")
    if security_rep:
        total = len(security_rep.get("findings", []))
        blocked = [
            f.get("license")
            for f in security_rep.get("findings", [])
            if f.get("category") == "license_blocked"
        ]
        badge = (
            "<span class='badge ok'>0</span>"
            if total == 0
            else f"<span class='badge fail'>{total}</span>"
        )
        parts.append(f"<div>Findings: {badge}</div>")
        if blocked:
            parts.append("<table>")
            parts.append(_row("Blocked Licenses", ", ".join(blocked)))
            parts.append("</table>")
    else:
        parts.append("<small>No security_report.json found.</small>")
    parts.append("</div>")

    html_text = "\n".join(parts)
    OUT_PATH.write_text(html_text, encoding="utf-8")
    print(f"Wrote scoreboard to {OUT_PATH}")

    # Emit JSON summary for regression gates
    summary = aggregate_json(runtime_reports, latency)
    (OUT_DIR / "latest.json").write_text(json.dumps(summary, indent=2))
    prev_path = OUT_DIR / "previous.json"
    if not prev_path.exists():
        prev_path.write_text(json.dumps(summary, indent=2))

    # Optional: also write a phase-tagged copy if PHASE env var set
    phase = os.environ.get("PHASE")
    if phase:
        phase_tag = phase if str(phase).startswith("phase-") else f"phase-{phase}"
        phase_out = OUT_DIR / f"{phase_tag}.html"
        phase_out.write_text(html_text, encoding="utf-8")
        print(f"Wrote phase scoreboard snapshot to {phase_out}")

        # Build a minimal JSON summary for history aggregation
        def _safe_get(d, *keys, default=None):
            cur = d or {}
            for k in keys:
                cur = (cur or {}).get(k, {})
            return cur if cur else default

        def _load(path):
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return None
        selfcheck = _load(ART_DIR / "selfcheck.json")
        eval_rep = _load(ART_DIR / "eval_report.json")
        latency = _load(ART_DIR / "latency.json")
        security_rep = _load(ART_DIR / "security_report.json")
        runtime_reports = []
        for p in glob.glob(str(ART_DIR / "*.build_eval_report.json")) + glob.glob(str(ART_DIR / "build_eval_report.json")):
            try:
                runtime_reports.append(_load(pathlib.Path(p)))
            except Exception:
                pass
        lint_py = _load(ART_DIR / "lint_python.json")
        lint_js = _load(ART_DIR / "lint_js.json")
        lint_cpp = _load(ART_DIR / "lint_cpp.json")

        rt_total = 0
        rt_passed = 0
        rt_skipped = 0
        for rep in runtime_reports or []:
            if not rep:
                continue
            if rep.get("skipped"):
                rt_skipped += 1
                continue
            rt_total += int(rep.get("total") or 0)
            rt_passed += int(rep.get("passed") or 0)

        sc_tools_ok = bool(_safe_get(selfcheck, "tools", "ok", default=False))
        sc_deny_ok = bool(_safe_get(selfcheck, "deny_rules", "ok", default=False))
        sc_skills_ok = bool(_safe_get(selfcheck, "skills", "ok", default=True))
        sc_latency_p50 = _safe_get(selfcheck, "latency", "p50_ms", default=None)
        sc_latency_budget = _safe_get(selfcheck, "latency", "budget_ms", default=None)
        sc_overall = sc_tools_ok and sc_deny_ok and sc_skills_ok and (
            sc_latency_p50 is None or (sc_latency_budget is None or sc_latency_p50 <= sc_latency_budget)
        )

        ev_rc = int(eval_rep.get("returncode", 0)) if isinstance(eval_rep, dict) else 0
        ev_ok = ev_rc == 0
        lat_p50 = latency.get("p50_sec") if isinstance(latency, dict) else None
        lat_mean = latency.get("mean_sec") if isinstance(latency, dict) else None
        sec_findings = len((security_rep or {}).get("findings", []))
        blocked = [
            f.get("license")
            for f in (security_rep or {}).get("findings", [])
            if f.get("category") == "license_blocked"
        ]

        summary = {
            "phase": phase_tag,
            "selfcheck": {
                "overall_ok": sc_overall,
                "tools_ok": sc_tools_ok,
                "deny_ok": sc_deny_ok,
                "skills_ok": sc_skills_ok,
                "latency_p50_ms": sc_latency_p50,
                "latency_budget_ms": sc_latency_budget,
            },
            "eval": {
                "ok": ev_ok,
                "returncode": ev_rc,
            },
            "latency": {
                "p50_sec": lat_p50,
                "mean_sec": lat_mean,
            },
            "runtime": {
                "passed": rt_passed,
                "total": rt_total,
                "reports_skipped": rt_skipped,
            },
            "security": {
                "findings": sec_findings,
                "whitelist": sorted(SPDX_WHITELIST),
                "blocked": blocked,
            },
            "lint": {
                "python": {
                    "ok": bool((lint_py or {}).get("ok")),
                    "issues": int((lint_py or {}).get("issues", 0)),
                },
                "web": {
                    "ok": bool((lint_js or {}).get("ok")),
                    "issues": int((lint_js or {}).get("issues", 0)),
                },
                "cpp": {
                    "ok": bool((lint_cpp or {}).get("ok")),
                    "issues": int((lint_cpp or {}).get("issues", 0)),
                },
            },
            "links": {
                "snapshot_html": phase_out.name,
            },
        }
        (OUT_DIR / f"{phase_tag}.summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
        print(f"Wrote phase summary: {OUT_DIR / (phase_tag + '.summary.json')}")

if __name__ == "__main__":
    main()
