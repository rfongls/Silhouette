#!/usr/bin/env python
"""
Aggregate phase scoreboards into a single history dashboard.
Scans for artifacts/scoreboard/phase-*.html and builds
artifacts/scoreboard/history.html listing each snapshot.
"""
import pathlib
import re
import time

ART_DIR = pathlib.Path("artifacts/scoreboard")
OUT_PATH = ART_DIR / "history.html"

def main():
    ART_DIR.mkdir(parents=True, exist_ok=True)
    snaps = []
    for p in sorted(ART_DIR.glob("phase-*.html")):
        m = re.match(r"phase-(\d+)\.html", p.name)
        if not m:
            continue
        snaps.append((int(m.group(1)), p.name))

    parts = []
    parts.append("<!doctype html><meta charset='utf-8'><title>Silhouette Scoreboard History</title>")
    parts.append("""
<style>
body{font-family:system-ui,Segoe UI,Roboto,Arial,sans-serif;margin:24px}
h1{margin:0 0 12px}
table{border-collapse:collapse;width:100%}
th,td{padding:6px 8px;border-bottom:1px solid #eee}
.phase{font-weight:600}
</style>
""")
    parts.append("<h1>Scoreboard History</h1>")
    parts.append(f"<div>Generated {time.strftime('%Y-%m-%d %H:%M:%S')}</div>")
    parts.append("<table>")
    parts.append("<tr><th>Phase</th><th>Snapshot Link</th></tr>")
    for phase, name in snaps:
        parts.append(f"<tr><td class='phase'>Phase {phase}</td><td><a href='{name}'>{name}</a></td></tr>")
    parts.append("</table>")
    OUT_PATH.write_text("\n".join(parts), encoding="utf-8")
    print(f"Wrote history dashboard: {OUT_PATH}")

if __name__ == "__main__":
    main()
