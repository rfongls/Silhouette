#!/usr/bin/env python
"""Render a history dashboard from phase scoreboard snapshots."""

import pathlib
import re
import time
import json
import html

ART_DIR = pathlib.Path("artifacts/scoreboard")
OUT = ART_DIR / "history.html"


def main():
    snaps = []
    for p in sorted(ART_DIR.glob("phase-*.html")):
        m = re.match(r"phase-(\d+)\.html", p.name)
        if not m:
            continue
        phase = int(m.group(1))
        snaps.append((phase, p))

    parts = []
    parts.append("<!doctype html><meta charset='utf-8'><title>Silhouette Scoreboard History — Cross-Language Agent Capability</title>")
    parts.append(
        """
<style>
body{font-family:system-ui,Segoe UI,Roboto,Arial,sans-serif;margin:24px}
h1{margin:0 0 12px} table{border-collapse:collapse;width:100%}
th,td{padding:6px 8px;border-bottom:1px solid #eee}
.phase{font-weight:600}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px}
.ok{background:#e6f4ea;color:#137333}
.fail{background:#fde8e8;color:#b91c1c}
.muted{color:#666}
</style>
"""
    )
    parts.append("<h1>Scoreboard History — Cross-Language Agent Capability</h1>")
    parts.append(f"<div>Generated {time.strftime('%Y-%m-%d %H:%M:%S')}</div>")
    parts.append("<table>")
    parts.append(
        "<tr><th>Phase</th><th>Selfcheck</th><th>Eval</th><th>Latency p50 (s)</th><th>Runtime (passed/total)</th><th>Security</th><th>Blocked Licenses</th><th>Snapshot</th></tr>"
    )

    prev_summary = None
    for phase, p in snaps:
        rel = p.name
        summary_path = ART_DIR / f"phase-{phase}.summary.json"
        sc_badge = "<span class='badge muted'>n/a</span>"
        ev_badge = "<span class='badge muted'>n/a</span>"
        lat_p50 = "—"
        rt_cell = "—"
        sec_cell = "—"
        blocked_cell = "—"
        trend_sc = ""
        trend_ev = ""
        trend_lat = ""
        trend_rt = ""
        if summary_path.exists():
            s = json.loads(summary_path.read_text(encoding="utf-8"))
            sc_ok = bool(((s.get("selfcheck") or {}).get("overall_ok")))
            ev_ok = bool(((s.get("eval") or {}).get("ok")))
            sc_cls = "ok" if sc_ok else "fail"
            sc_txt = "OK" if sc_ok else "FAIL"
            sc_badge = f"<span class='badge {sc_cls}'>{sc_txt}</span>"
            ev_cls = "ok" if ev_ok else "fail"
            ev_txt = "OK" if ev_ok else "FAIL"
            ev_badge = f"<span class='badge {ev_cls}'>{ev_txt}</span>"
            lat = (s.get("latency") or {}).get("p50_sec")
            lat_p50 = f"{lat:.3f}" if isinstance(lat, (int, float)) else "—"
            rt = s.get("runtime") or {}
            rt_cell = f"{rt.get('passed',0)}/{rt.get('total',0)}"
            if int(rt.get('reports_skipped',0)) > 0:
                rt_cell += f" <span class='muted'>(skipped {rt.get('reports_skipped')})</span>"
            sec = (s.get("security") or {}).get("findings")
            sec_cell = "0" if sec in (0, None) else str(sec)
            blocked_list = (s.get("security") or {}).get("blocked", []) or []
            blocked_cell = ", ".join(blocked_list) if blocked_list else "—"

            if prev_summary:
                prev_sc = bool(((prev_summary.get("selfcheck") or {}).get("overall_ok")))
                trend_sc = "▲" if sc_ok and not prev_sc else ("▼" if prev_sc and not sc_ok else "▬")
                prev_ev = bool(((prev_summary.get("eval") or {}).get("ok")))
                trend_ev = "▲" if ev_ok and not prev_ev else ("▼" if prev_ev and not ev_ok else "▬")
                prev_lat = (prev_summary.get("latency") or {}).get("p50_sec")
                if isinstance(lat, (int, float)) and isinstance(prev_lat, (int, float)):
                    if lat < prev_lat:
                        trend_lat = "▲"
                    elif lat > prev_lat:
                        trend_lat = "▼"
                    else:
                        trend_lat = "▬"
                prev_pass = (prev_summary.get("runtime") or {}).get("passed", 0)
                prev_tot = (prev_summary.get("runtime") or {}).get("total", 0)
                cur_pass, cur_tot = rt.get("passed", 0), rt.get("total", 0)
                prev_ratio = prev_pass / max(prev_tot, 1)
                cur_ratio = cur_pass / max(cur_tot, 1)
                if cur_ratio > prev_ratio:
                    trend_rt = "▲"
                elif cur_ratio < prev_ratio:
                    trend_rt = "▼"
                else:
                    trend_rt = "▬"
            prev_summary = s

        parts.append(
            f"<tr>"
            f"<td class='phase'>Phase {phase}</td>"
            f"<td>{sc_badge} {trend_sc}</td>"
            f"<td>{ev_badge} {trend_ev}</td>"
            f"<td>{lat_p50} {trend_lat}</td>"
            f"<td>{rt_cell} {trend_rt}</td>"
            f"<td>{sec_cell}</td><td>{html.escape(blocked_cell)}</td><td><a href='{rel}'>{html.escape(rel)}</a></td>"
            f"</tr>"
        )

    parts.append("</table>")
    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"Wrote history dashboard: {OUT}")


if __name__ == "__main__":
    main()
