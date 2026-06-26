"""Tests for PatternSeparation (Dentate Gyrus analog).

Pattern separation: distinguish similar-but-different contexts by computing
entity fingerprints and Jaccard similarity. Prevents context contamination.
"""

from synapse.hippocampus.pattern_separation import PatternSeparation


def test_identical_fingerprints_high_similarity():
    """Two entities with identical edge sets should have 1.0 similarity."""
    edges_a = [
        {"from_node": "A", "fact": "A uses X", "to_node": "X"},
        {"from_node": "A", "fact": "A uses Y", "to_node": "Y"},
    ]
    edges_b = [
        {"from_node": "B", "fact": "B uses X", "to_node": "X"},
        {"from_node": "B", "fact": "B uses Y", "to_node": "Y"},
    ]
    ps = PatternSeparation()
    sim = ps.entity_similarity("A", "B", edges_a + edges_b)
    # A connects to {X, Y}, B connects to {X, Y} → Jaccard = 1.0
    assert sim == 1.0


def test_disjoint_fingerprints_zero_similarity():
    """Two entities with completely different connections should have 0.0."""
    edges = [
        {"from_node": "A", "fact": "A uses X", "to_node": "X"},
        {"from_node": "B", "fact": "B uses Z", "to_node": "Z"},
    ]
    ps = PatternSeparation()
    sim = ps.entity_similarity("A", "B", edges)
    assert sim == 0.0


def test_partial_similarity():
    """Partially overlapping connections should give intermediate similarity."""
    edges = [
        {"from_node": "A", "fact": "A uses X", "to_node": "X"},
        {"from_node": "A", "fact": "A uses Y", "to_node": "Y"},
        {"from_node": "B", "fact": "B uses X", "to_node": "X"},
        {"from_node": "B", "fact": "B uses Z", "to_node": "Z"},
    ]
    ps = PatternSeparation()
    sim = ps.entity_similarity("A", "B", edges)
    # A: {X, Y}, B: {X, Z}, intersection: {X}, union: {X, Y, Z}
    # Jaccard = 1/3 ≈ 0.333
    assert 0.30 < sim < 0.40


def test_should_separate_high_similarity():
    """High similarity above threshold should flag for separation."""
    ps = PatternSeparation(similarity_threshold=0.7)
    edges = [
        {"from_node": "A", "fact": "A uses X", "to_node": "X"},
        {"from_node": "B", "fact": "B uses X", "to_node": "X"},
    ]
    sim = ps.entity_similarity("A", "B", edges)
    assert ps.should_separate(sim)  # 1.0 > 0.7


def test_should_not_separate_low_similarity():
    """Low similarity should not flag."""
    ps = PatternSeparation(similarity_threshold=0.7)
    assert not ps.should_separate(0.3)


def test_entity_fingerprint():
    """Fingerprint should be the set of connected entities."""
    edges = [
        {"from_node": "A", "fact": "A uses X", "to_node": "X"},
        {"from_node": "A", "fact": "A uses Y", "to_node": "Y"},
        {"from_node": "B", "fact": "B uses Z", "to_node": "Z"},
    ]
    ps = PatternSeparation()
    fp = ps.fingerprint("A", edges)
    assert fp == {"X", "Y"}


def test_find_similar_pairs():
    """Should find all pairs above the similarity threshold."""
    edges = [
        {"from_node": "A", "fact": "A uses X", "to_node": "X"},
        {"from_node": "A", "fact": "A uses Y", "to_node": "Y"},
        {"from_node": "B", "fact": "B uses X", "to_node": "X"},
        {"from_node": "B", "fact": "B uses Y", "to_node": "Y"},
        {"from_node": "C", "fact": "C uses Z", "to_node": "Z"},
    ]
    ps = PatternSeparation(similarity_threshold=0.5)
    pairs = ps.find_similar_pairs(["A", "B", "C"], edges)
    # A-B are similar (1.0), A-C and B-C are not (0.0)
    assert any(p["entity_a"] == "A" and p["entity_b"] == "B" for p in pairs)
    assert not any(p["entity_a"] == "A" and p["entity_b"] == "C" for p in pairs)
