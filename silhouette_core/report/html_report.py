from __future__ import annotations

from pathlib import Path

try:  # pragma: no cover - optional dependency
    from jinja2 import Environment, FileSystemLoader
except Exception:  # pragma: no cover - jinja2 not installed
    Environment = None  # type: ignore[assignment]


def render_repo_map_html(repo_map: dict, out_html_path: str | Path) -> None:
    """Render ``repo_map`` into an HTML report at ``out_html_path``.

    Uses Jinja2 when available; otherwise falls back to a very small
    string-based renderer.  The output is deterministic and self-contained.
    """

    out_path = Path(out_html_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if Environment is not None:
        tmpl_dir = Path(__file__).resolve().parent / "templates"
        env = Environment(loader=FileSystemLoader(str(tmpl_dir)))
        tmpl = env.get_template("report.html.j2")
        html = tmpl.render(repo=repo_map)
    else:  # pragma: no cover - fallback path
        lines: list[str] = [
            "<html><head><meta charset='utf-8'><title>Repo Report</title>",
            "<style>section{margin-bottom:1em}.risk{background:#fcc;padding:0 4px}</style>",
            "</head><body>",
            "<section id='overview'><h1>Repo Report</h1></section>",
            "<section id='hotspots'><h2>Hotspots</h2><table>",
        ]
        for node in repo_map.get("top_centrality_nodes", []):
            lines.append(
                f"<tr><td>{node['path']}</td><td>{node['centrality']:.2f}</td></tr>"
            )
        lines.extend(["</table></section>", "<section id='services'>"])
        for svc in repo_map.get("services", []):
            owners = ", ".join(svc.get("owners", [])) or "none"
            risks = " ".join(
                f"<span class='risk'>{r}</span>"
                for r, items in svc.get("risks", {}).items()
                if items
            )
            lines.append(
                f"<div class='card'><h3>{svc['name']}</h3><p>Owners: {owners}</p><p>{risks}</p></div>"
            )
        lines.extend(
            [
                "</section>",
                "<section id='entrypoints'><ul>" + "".join(
                    f"<li>{e}</li>" for e in repo_map.get("entrypoints", [])
                ) + "</ul></section>",
                '<section id="links"><a href="repo_map.json">View JSON</a></section>',
                "</body></html>",
            ]
        )
        html = "\n".join(lines)
    out_path.write_text(html, encoding="utf-8")
