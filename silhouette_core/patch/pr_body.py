from __future__ import annotations


def compose_pr_body(goal: str, impact: dict, summary: dict) -> str:
    lines = []
    lines.append("## Context / Goal\n")
    lines.append(goal + "\n\n")
    lines.append("## Changes Summary\n")
    lines.append(
        f"Files changed: {', '.join(summary.get('files_changed', []))}\n"
        f"Insertions: {summary.get('insertions', 0)}, Deletions: {summary.get('deletions', 0)}\n\n"
    )
    lines.append("## Impact Set\n")
    lines.append("### Modules\n" + "\n".join(f"- {m}" for m in impact.get("modules", [])) + "\n")
    tests = impact.get("tests", {})
    lines.append("### Tests\n")
    lines.append("#### Must Run\n" + ("\n".join(f"- {t}" for t in tests.get("must_run", [])) or "- none") + "\n")
    lines.append("#### Suggested\n" + ("\n".join(f"- {t}" for t in tests.get("suggested", [])) or "- none") + "\n")
    docs = impact.get("docs", {})
    lines.append("### Docs\n" + ("\n".join(f"- {d}" for d in docs.get("suggested", [])) or "- none") + "\n")
    lines.append("## Risks & Mitigations\n- TBD\n")
    lines.append("## Test Plan\n")
    for t in tests.get("must_run", []):
        lines.append(f"- pytest -q {t}\n")
    lines.append("## Checklist\n- [ ] CI passes\n- [ ] Docs updated\n")
    return "".join(lines)
