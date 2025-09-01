import json


def tool(passages_json: str) -> str:
    """
    Input: passages from research_retrieve
    Output: {"citations":[{"ref":"[1]","doc_id":..,"section_id":..},...]}
    """
    pas = json.loads(passages_json or "[]")
    cites = [
        {"ref": f"[{i+1}]", "doc_id": p["doc_id"], "section_id": p["section_id"]}
        for i, p in enumerate(pas)
    ]
    return json.dumps({"citations": cites})

