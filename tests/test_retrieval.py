"""Tests for RetrievalEngine."""

from synapse.retrieval import RetrievalEngine


def test_bm25_query_builder():
    """BM25 query should not use LLM — pure Cypher fulltext search."""
    engine = RetrievalEngine(host="localhost", port=6379, group_id="test")
    query = engine._build_bm25_query("temporal knowledge graph", limit=5)
    assert "RELATES_TO" in query
    assert "fact" in query
    assert "LIMIT 5" in query


def test_cache_key_generation():
    engine = RetrievalEngine(host="localhost", port=6379, group_id="test")
    key = engine._cache_key("what is Synapse?")
    assert isinstance(key, str)
    assert len(key) > 0


def test_format_results():
    """Results should be formatted as context for the system prompt."""
    engine = RetrievalEngine(host="localhost", port=6379, group_id="test")
    edges = [
        {"fact": "Synapse uses FalkorDB", "from_node": "Synapse", "to_node": "FalkorDB"},
        {"fact": "Synapse uses Graphiti", "from_node": "Synapse", "to_node": "Graphiti"},
    ]
    formatted = engine._format_results(edges)
    assert "Synapse uses FalkorDB" in formatted
    assert "Synapse uses Graphiti" in formatted


def test_format_empty_results():
    """Empty results should return empty string."""
    engine = RetrievalEngine(host="localhost", port=6379, group_id="test")
    assert engine._format_results([]) == ""


def test_prefetch_returns_cached():
    """prefetch() should return cached result from queue_prefetch()."""
    engine = RetrievalEngine(host="localhost", port=6379, group_id="test")
    # No cache → empty string
    assert engine.prefetch("anything") == ""

    # Manually inject cache
    engine._cache[engine._cache_key("test query")] = "cached context"
    assert engine.prefetch("test query") == "cached context"
