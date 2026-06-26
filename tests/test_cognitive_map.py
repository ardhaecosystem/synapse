"""Tests for CognitiveMap."""

from synapse.hippocampus.cognitive_map import CognitiveMap


def test_shortest_path_direct():
    """Directly connected entities should have path length 1."""
    edges = [
        {"from_node": "A", "fact": "A uses B", "to_node": "B"},
    ]
    cm = CognitiveMap(edges)
    path = cm.shortest_path("A", "B")
    assert path == ["A", "B"]


def test_shortest_path_two_hops():
    """Two-hop path should be found."""
    edges = [
        {"from_node": "A", "fact": "A uses B", "to_node": "B"},
        {"from_node": "B", "fact": "B uses C", "to_node": "C"},
    ]
    cm = CognitiveMap(edges)
    path = cm.shortest_path("A", "C")
    assert path == ["A", "B", "C"]


def test_no_path_returns_empty():
    """Disconnected entities should return empty path."""
    edges = [
        {"from_node": "A", "fact": "A uses B", "to_node": "B"},
        {"from_node": "C", "fact": "C uses D", "to_node": "D"},
    ]
    cm = CognitiveMap(edges)
    path = cm.shortest_path("A", "D")
    assert path == []


def test_neighborhood():
    """1-hop neighborhood should return directly connected entities."""
    edges = [
        {"from_node": "A", "fact": "A uses B", "to_node": "B"},
        {"from_node": "A", "fact": "A uses C", "to_node": "C"},
        {"from_node": "B", "fact": "B uses D", "to_node": "D"},
    ]
    cm = CognitiveMap(edges)
    neighbors = cm.neighborhood("A", depth=1)
    assert "B" in neighbors
    assert "C" in neighbors
    assert "D" not in neighbors  # 2-hop, beyond depth=1


def test_neighborhood_two_hops():
    """2-hop neighborhood should include 2-hop entities."""
    edges = [
        {"from_node": "A", "fact": "A uses B", "to_node": "B"},
        {"from_node": "B", "fact": "B uses D", "to_node": "D"},
    ]
    cm = CognitiveMap(edges)
    neighbors = cm.neighborhood("A", depth=2)
    assert "B" in neighbors
    assert "D" in neighbors


def test_all_entities():
    """Should return all unique entities in the graph."""
    edges = [
        {"from_node": "A", "fact": "A uses B", "to_node": "B"},
        {"from_node": "C", "fact": "C uses D", "to_node": "D"},
    ]
    cm = CognitiveMap(edges)
    entities = cm.all_entities()
    assert entities == {"A", "B", "C", "D"}
