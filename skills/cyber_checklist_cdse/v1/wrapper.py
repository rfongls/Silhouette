import json, pathlib

INDEX = pathlib.Path("docs/cyber/cdse/toolkit_index.json")

def tool(domain: str) -> str:
    """
    domain: e.g., "system management", "incident response"
    Returns: {"domain": "...", "items":[{"title":..., "ref":"[1]", "doc_id":..., "section_id":...}]}
    """
    if not INDEX.exists():
        return json.dumps({"ok": False, "error": "missing_index", "path": str(INDEX)})
    data = json.loads(INDEX.read_text())
    dom = domain.lower()
    items = []
    for e in data:
        hay = (e["title"] + " " + e["text"]).lower()
        if dom in hay:
            items.append({
                "title": e["title"],
                "ref": "[1]",
                "doc_id": e["doc_id"],
                "section_id": e["section_id"]
            })
    return json.dumps({"ok": True, "domain": domain, "items": items[:10]})
