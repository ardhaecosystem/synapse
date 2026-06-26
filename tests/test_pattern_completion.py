"""Tests for PatternCompletion (CA3 analog).

Pattern completion: given a partial cue (BM25 match), retrieve the full
subgraph by expanding to the 2-hop neighborhood of matched entities.
"""

from synapse.hippocampus.pattern_completion import PatternCompletion


def test_complete_empty_edges():
    """Empty edge list should return empty result."""
    pc = PatternCompletion(group_id="test")
    result = pc.complete("query", [])
    assert result["facts"] == []
    assert result["entities"] == []


def test_complete_returns_matching_facts():
    """Facts that match the query should be returned."""
    edges = [
        {"from_node": "Synapse", "fact": "Synapse uses FalkorDB for storage",
         "to_node": "FalkorDB", "valid_at": "2026-01-01", "invalid_at": None},
    ]
    pc = PatternCompletion(group_id="test")
    result = pc.complete("FalkorDB", edges)
    assert len(result["facts"]) >= 1
    assert "FalkorDB" in result["facts"][0]["fact"]


def test_complete_expands_to_neighbors():
    """Pattern completion should expand to neighbors of matched entities."""
    edges = [
        {"from_node": "Synapse", "fact": "Synapse uses FalkorDB for storage",
         "to_node": "FalkorDB", "valid_at": "2026-01-01", "invalid_at": None},
        {"from_node": "Synapse", "fact": "Synapse uses Graphiti for temporal modeling",
         "to_node": "Graphiti", "valid_at": "2026-01-01", "invalid_at": None},
        {"from_node": "FalkorDB", "fact": "FalkorDB runs in Docker",
         "to_node": "Docker", "valid_at": "2026-01-01", "invalid_at": None},
    ]
    pc = PatternCompletion(group_id="test")
    result = pc.complete("FalkorDB", edges)
    # Should return the direct match (FalkorDB) AND expanded neighbors (Graphiti, Docker)
    entities = result["entities"]
    assert "FalkorDB" in entities
    assert "Synapse" in entities  # 1-hop neighbor
    assert "Graphiti" in entities  # 2-hop via Synapse
    assert "Docker" in entities  # 1-hop from FalkorDB


def test_complete_respects_max_depth():
    """Max depth should limit the expansion."""
    edges = [
        {"from_node": "A", "fact": "A relates to B", "to_node": "B",
         "valid_at": "2026-01-01", "invalid_at": None},
        {"from_node": "B", "fact": "B relates to C", "to_node": "C",
         "valid_at": "2026-01-01", "invalid_at": None},
        {"from_node": "C", "fact": "C relates to D", "to_node": "D",
         "valid_at": "2026-01-01", "invalid_at": None},
    ]
    pc = PatternCompletion(group_id="test", max_depth=1)
    result = pc.complete("A relates", edges)
    # Query matches "A relates to B" → matched = {A, B}
    # max_depth=1: A's neighbors (B) and B's neighbors (C) are included
    # But D (2 hops from B, 3 from A) should NOT be included
    assert "A" in result["entities"]
    assert "B" in result["entities"]
    assert "C" in result["entities"]  # 1-hop from B (matched entity)
    assert "D" not in result["entities"]  # 2-hop from B, beyond max_depth


def test_complete_excludes_invalidated():
    """Invalidated edges should not be included in the completed pattern."""
    edges = [
        {"from_node": "A", "fact": "A uses X", "to_node": "X",
         "valid_at": "2026-01-01", "invalid_at": "2026-01-03"},
        {"from_node": "A", "fact": "A uses Y", "to_node": "Y",
         "valid_at": "2026-01-03", "invalid_at": None},
    ]
    pc = PatternCompletion(group_id="test")
    result = pc.complete("A", edges)
    facts = [f["fact"] for f in result["facts"]]
    assert "A uses Y" in facts
    assert "A uses X" not in facts  # invalidated
