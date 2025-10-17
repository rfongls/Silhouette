from __future__ import annotations
from pathlib import Path
from typing import Optional
import os

# Search order (highest priority first)
SEARCH_ROOTS = [
    Path("templates/standalone"),         # repo's standalone templates (if any)
    Path("templates/standalone/legacy"),  # vendored legacy templates (from working zip)
]

def find_template(rel_name: str) -> Optional[str]:
    """
    Return the filesystem path to the first matching template in SEARCH_ROOTS.
    rel_name is a filename like '_generate_panel.html' or 'index.html'.
    """
    override = os.getenv("STANDALONE_TEMPLATE_ROOT")
    roots = [Path(override)] + SEARCH_ROOTS if override else SEARCH_ROOTS
    for root in roots:
        p = root / rel_name
        if p.exists():
            return str(p)
    return None

def resolve_include(rel_name: str) -> str:
    """
    Return a Jinja include path for a template, preferring standalone/**, else legacy/**.
    """
    p = find_template(rel_name)
    if not p:
        return f"standalone/{rel_name}"
    pth = Path(p)
    # Normalize to a Jinja loader-relative path
    if "templates/standalone/legacy" in str(pth):
        return "standalone/legacy/" + rel_name
    return "standalone/" + rel_name
