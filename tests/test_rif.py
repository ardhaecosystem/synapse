"""Tests for retrieval-induced forgetting (RIF) in the Hippocampus coordinator."""

from synapse.hippocampus import Hippocampus


def test_rif_no_penalty_without_recall():
    """Entities with no recall should have 0 penalty."""
    hp = Hippocampus()
    assert hp.get_rif_penalty("A") == 0.0


def test_rif_penalizes_competitors():
    """Recalling entity A should penalize similar-but-not-recalled entities."""
    hp = Hippocampus()
    # Build edges where A and B share many connections (high Jaccard)
    edges = [
        {"from_node": "A", "to_node": "X", "fact": "A uses X",
         "valid_at": "2026-01-01T00:00:00Z", "invalid_at": None},
        {"from_node": "A", "to_node": "Y", "fact": "A uses Y",
         "valid_at": "2026-01-01T00:00:00Z", "invalid_at": None},
        {"from_node": "B", "to_node": "X", "fact": "B uses X",
         "valid_at": "2026-01-01T00:00:00Z", "invalid_at": None},
        {"from_node": "B", "to_node": "Y", "fact": "B uses Y",
         "valid_at": "2026-01-01T00:00:00Z", "invalid_at": None},
    ]
    # Recall A — B is Jaccard-similar (same connections: X, Y)
    hp.on_recall(["A"], edges=edges)
    # B should have a penalty
    assert hp.get_rif_penalty("B") > 0.0
    # A should NOT be penalized (it was recalled)
    assert hp.get_rif_penalty("A") == 0.0


def test_rif_does_not_penalize_dissimilar():
    """Dissimilar entities should not be penalized."""
    hp = Hippocampus()
    edges = [
        {"from_node": "A", "to_node": "X", "fact": "A uses X",
         "valid_at": "2026-01-01T00:00:00Z", "invalid_at": None},
        {"from_node": "C", "to_node": "Z", "fact": "C uses Z",
         "valid_at": "2026-01-01T00:00:00Z", "invalid_at": None},
    ]
    hp.on_recall(["A"], edges=edges)
    # C shares nothing with A — no penalty
    assert hp.get_rif_penalty("C") == 0.0


def test_rif_skipped_without_edges():
    """on_recall without edges should skip RIF (only reconsolidation)."""
    hp = Hippocampus()
    hp.on_recall(["A"], edges=None)
    assert hp.get_rif_penalty("A") == 0.0
    # But reconsolidation still ran
    assert "A" in hp.get_active_entities()


def test_rif_expires_with_reconsolidation_window():
    """RIF penalties should expire when the reconsolidation window closes."""
    hp = Hippocampus()
    edges = [
        {"from_node": "A", "to_node": "X", "fact": "A uses X",
         "valid_at": "2026-01-01T00:00:00Z", "invalid_at": None},
        {"from_node": "A", "to_node": "Y", "fact": "A uses Y",
         "valid_at": "2026-01-01T00:00:00Z", "invalid_at": None},
        {"from_node": "B", "to_node": "X", "fact": "B uses X",
         "valid_at": "2026-01-01T00:00:00Z", "invalid_at": None},
        {"from_node": "B", "to_node": "Y", "fact": "B uses Y",
         "valid_at": "2026-01-01T00:00:00Z", "invalid_at": None},
    ]
    hp.on_recall(["A"], edges=edges)
    assert hp.get_rif_penalty("B") > 0.0

    # Advance past the reconsolidation window (default 10 turns)
    for _ in range(11):
        hp.tick()

    # A's reconsolidation window expired → B's penalty expired too
    assert hp.get_rif_penalty("B") == 0.0


def test_rif_clear_resets_penalties():
    """clear() should reset all RIF penalties."""
    hp = Hippocampus()
    edges = [
        {"from_node": "A", "to_node": "X", "fact": "A uses X",
         "valid_at": "2026-01-01T00:00:00Z", "invalid_at": None},
        {"from_node": "A", "to_node": "Y", "fact": "A uses Y",
         "valid_at": "2026-01-01T00:00:00Z", "invalid_at": None},
        {"from_node": "B", "to_node": "X", "fact": "B uses X",
         "valid_at": "2026-01-01T00:00:00Z", "invalid_at": None},
        {"from_node": "B", "to_node": "Y", "fact": "B uses Y",
         "valid_at": "2026-01-01T00:00:00Z", "invalid_at": None},
    ]
    hp.on_recall(["A"], edges=edges)
    assert hp.get_rif_penalty("B") > 0.0
    hp.clear()
    assert hp.get_rif_penalty("B") == 0.0


def test_rif_penalized_entity_recoverable():
    """A penalized entity should still be in the system — penalty is ranking only."""
    hp = Hippocampus()
    edges = [
        {"from_node": "A", "to_node": "X", "fact": "A uses X",
         "valid_at": "2026-01-01T00:00:00Z", "invalid_at": None},
        {"from_node": "A", "to_node": "Y", "fact": "A uses Y",
         "valid_at": "2026-01-01T00:00:00Z", "invalid_at": None},
        {"from_node": "B", "to_node": "X", "fact": "B uses X",
         "valid_at": "2026-01-01T00:00:00Z", "invalid_at": None},
        {"from_node": "B", "to_node": "Y", "fact": "B uses Y",
         "valid_at": "2026-01-01T00:00:00Z", "invalid_at": None},
    ]
    hp.on_recall(["A"], edges=edges)
    penalty = hp.get_rif_penalty("B")
    # Penalty is non-zero but less than 1.0 — entity is suppressed, not deleted
    assert 0.0 < penalty < 1.0
