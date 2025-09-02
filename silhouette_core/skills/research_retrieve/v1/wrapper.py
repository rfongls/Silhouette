import json, sqlite3

INDEX = "artifacts/index/research.db"


def tool(payload: str) -> str:
    """
    Input: JSON like {"query":"...", "k":3}
    Output: JSON list of passages with ids + text
    """
    data = json.loads(payload or "{}")
    query = data.get("query", "")
    k = int(data.get("k", 3))
    conn = sqlite3.connect(INDEX)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT doc_id, section_id, text, rank FROM passages WHERE passages MATCH ? ORDER BY rank LIMIT ?",
        (query, k),
    ).fetchall()
    return json.dumps([dict(r) for r in rows])

