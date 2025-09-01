import json, pathlib

INDEX = pathlib.Path("docs/cyber/cdse/toolkit_index.json")

def tool(query: str) -> str:
    """
    query: keywords, e.g. "baseline configuration"
    Returns: {"results":[{"ref":"[n]","doc_id":...,"section_id":...,"snippet":...}]}
    """
    if not INDEX.exists():
        return json.dumps({"ok": False, "error": "missing_index"})
    data = json.loads(INDEX.read_text())
    q = query.lower()
    out = []
    for e in data:
        if q in (e["title"] + " " + e["text"]).lower():
            snippet = e["text"][:400].replace("\n", " ")
            out.append({"ref": f"[{len(out)+1}]", "doc_id": e["doc_id"], "section_id": e["section_id"], "snippet": snippet})
            if len(out) >= 5:
                break
    return json.dumps({"ok": True, "results": out})
