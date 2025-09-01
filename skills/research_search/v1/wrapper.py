import json, sqlite3

INDEX = "artifacts/index/research.db"


def tool(query: str, k: int = 5) -> str:
    """
    Input: query string
    Output: JSON list [{"doc_id":..,"section_id":..,"text":..,"rank":..}, ...]
    """
    conn = sqlite3.connect(INDEX)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT doc_id, section_id, text, rank FROM passages WHERE passages MATCH ? ORDER BY rank LIMIT ?",
        (query, k),
    ).fetchall()
    out = [
        {"doc_id": r["doc_id"], "section_id": r["section_id"], "text": r["text"], "rank": i + 1}
        for i, r in enumerate(rows)
    ]
    return json.dumps(out)

