"""Tests for ConsolidationEngine."""

from synapse.hippocampus.consolidation import ConsolidationEngine


def test_contradiction_detection_via_invalid_at():
    """Edges with invalid_at set indicate superseded facts."""
    edges = [
        {"from_node": "A", "fact": "A uses X", "to_node": "X",
         "valid_at": "2026-01-01", "invalid_at": "2026-01-03"},
        {"from_node": "A", "fact": "A uses Y instead of X", "to_node": "Y",
         "valid_at": "2026-01-03", "invalid_at": None},
    ]
    engine = ConsolidationEngine()
    contradictions = engine.detect_contradictions(edges)
    assert len(contradictions) >= 1
    assert contradictions[0]["type"] == "supersession"


def test_hebbian_co_occurrence():
    """Entities in the same episode (same valid_at timestamp) co-occur."""
    edges = [
        {"from_node": "A", "fact": "f1", "to_node": "B",
         "valid_at": "2026-01-01T10:00:00", "invalid_at": None},
        {"from_node": "A", "fact": "f2", "to_node": "C",
         "valid_at": "2026-01-01T10:00:00", "invalid_at": None},
        {"from_node": "B", "fact": "f3", "to_node": "C",
         "valid_at": "2026-01-02T10:00:00", "invalid_at": None},
    ]
    engine = ConsolidationEngine()
    co_occurrences = engine.hebbian_strengthening(edges)
    assert len(co_occurrences) >= 1
    # First timestamp has 3 entities (A, B, C)
    assert len(co_occurrences[0]["entities"]) >= 2


def test_no_contradictions_returns_empty():
    edges = [
        {"from_node": "A", "fact": "A uses X", "to_node": "X",
         "valid_at": "2026-01-01", "invalid_at": None},
    ]
    engine = ConsolidationEngine()
    contradictions = engine.detect_contradictions(edges)
    assert len(contradictions) == 0


def test_keyword_correction_detection():
    """Keyword patterns should also be detected."""
    edges = [
        {"from_node": "A", "fact": "A uses MongoDB instead of PostgreSQL",
         "to_node": "MongoDB", "valid_at": "2026-01-01", "invalid_at": None},
    ]
    engine = ConsolidationEngine()
    contradictions = engine.detect_contradictions(edges)
    assert any(c["type"] == "keyword_correction" for c in contradictions)
