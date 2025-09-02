from silhouette_core.embedding_engine import query_knowledge

def test_query_returns_results():
    results = query_knowledge(prompt="HL7 delimiter")
    assert isinstance(results, list)
    assert all("score" in r for r in results)
