from __future__ import annotations
from pathlib import Path
from typing import Optional, Tuple
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

def resolve_include(rel_name: str) -> Tuple[str, str]:
    """
    Return (jinja_path, source_fs_path). Prefer templates/standalone/**, then legacy/**.
    If neither exists, return legacy path as jinja_path so missing files are obvious.
    """
    p = find_template(rel_name)
    if p:
        pth = Path(p)
        if "templates/standalone/legacy" in str(pth):
            return "standalone/legacy/" + rel_name, p
        return "standalone/" + rel_name, p
    legacy_guess = Path("templates/standalone/legacy") / rel_name
    return "standalone/legacy/" + rel_name, str(legacy_guess)
