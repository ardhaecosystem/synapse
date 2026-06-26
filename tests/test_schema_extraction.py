"""Tests for SchemaExtraction (Neocortex analog — the slow learning system).

Schema extraction: periodically clusters entities by topic and creates
higher-level "schema nodes" that generalize from individual episodic memories.
"""

from synapse.hippocampus.schema_extraction import SchemaExtractor


def test_empty_edges_no_schemas():
    """Empty edge list should produce no schemas."""
    extractor = SchemaExtractor()
    schemas = extractor.extract([])
    assert schemas == []


def test_single_cluster_one_schema():
    """A connected cluster should produce one schema."""
    edges = [
        {"from_node": "Synapse", "fact": "Synapse uses FalkorDB", "to_node": "FalkorDB"},
        {"from_node": "Synapse", "fact": "Synapse uses Graphiti", "to_node": "Graphiti"},
        {"from_node": "Synapse", "fact": "Synapse is MIT licensed", "to_node": "MIT"},
    ]
    extractor = SchemaExtractor(min_cluster_size=2)
    schemas = extractor.extract(edges)
    assert len(schemas) >= 1
    assert "Synapse" in schemas[0]["entities"]


def test_disconnected_clusters_separate_schemas():
    """Disconnected clusters should produce separate schemas."""
    edges = [
        {"from_node": "A", "fact": "A uses X", "to_node": "X"},
        {"from_node": "B", "fact": "B uses Z", "to_node": "Z"},
    ]
    extractor = SchemaExtractor(min_cluster_size=1)
    schemas = extractor.extract(edges)
    # A-X is one cluster, B-Z is another
    entity_sets = [set(s["entities"]) for s in schemas]
    assert any({"A", "X"} <= es for es in entity_sets)
    assert any({"B", "Z"} <= es for es in entity_sets)


def test_schema_has_summary():
    """Each schema should have a summary string."""
    edges = [
        {"from_node": "A", "fact": "A uses X", "to_node": "X"},
        {"from_node": "A", "fact": "A uses Y", "to_node": "Y"},
    ]
    extractor = SchemaExtractor(min_cluster_size=2)
    schemas = extractor.extract(edges)
    assert len(schemas) >= 1
    assert "summary" in schemas[0]
    assert len(schemas[0]["summary"]) > 0


def test_schema_fact_count():
    """Schema should report how many facts it covers."""
    edges = [
        {"from_node": "A", "fact": "A uses X", "to_node": "X"},
        {"from_node": "A", "fact": "A uses Y", "to_node": "Y"},
        {"from_node": "X", "fact": "X enables Y", "to_node": "Y"},
    ]
    extractor = SchemaExtractor(min_cluster_size=2)
    schemas = extractor.extract(edges)
    assert len(schemas) >= 1
    assert schemas[0]["fact_count"] >= 2


def test_min_cluster_size_filters():
    """Clusters smaller than min_cluster_size should be filtered out."""
    edges = [
        {"from_node": "A", "fact": "A uses X", "to_node": "X"},
        {"from_node": "B", "fact": "B uses Y", "to_node": "Y"},
        {"from_node": "B", "fact": "B uses Z", "to_node": "Z"},
        {"from_node": "Y", "fact": "Y relates to Z", "to_node": "Z"},
    ]
    # A-X cluster has 2 entities; B-Y-Z cluster has 3 entities
    extractor = SchemaExtractor(min_cluster_size=3)
    schemas = extractor.extract(edges)
    # Only the B-Y-Z cluster (3 entities) should pass
    all_schema_entities = set()
    for s in schemas:
        all_schema_entities.update(s["entities"])
    assert "B" in all_schema_entities
    assert "A" not in all_schema_entities
