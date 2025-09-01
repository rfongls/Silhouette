import json, sqlite3, pathlib

INDEX = "artifacts/index/research.db"


def _ensure_schema(conn):
    conn.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS passages USING fts5(doc_id, section_id, text);"
    )
    conn.commit()


def tool(sections_json: str) -> str:
    """
    Input: JSON list from research_read_pdf
    Behavior: insert sections into SQLite FTS index
    """
    pathlib.Path("artifacts/index").mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(INDEX)
    _ensure_schema(conn)
    docs = json.loads(sections_json)
    with conn:
        for d in docs:
            conn.execute(
                "INSERT INTO passages(doc_id, section_id, text) VALUES(?,?,?)",
                (d["doc_id"], d["section_id"], d["text"]),
            )
    return json.dumps({"indexed": len(docs), "index": INDEX})

