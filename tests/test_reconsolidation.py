"""Tests for Reconsolidation.

Reconsolidation: when a memory is recalled, it becomes "active" for a
configurable window. During this window, new information about the recalled
entity gets a salience boost, and contradictions get priority processing.
"""

from synapse.hippocampus.reconsolidation import ReconsolidationTracker


def test_recall_increments_counter():
    """Recalling an entity should increment its recall counter."""
    tracker = ReconsolidationTracker(window_turns=10)
    tracker.recall("Synapse")
    tracker.recall("Synapse")
    tracker.recall("Synapse")
    assert tracker.get_recall_count("Synapse") == 3


def test_recall_activates_entity():
    """Recalling should mark the entity as active."""
    tracker = ReconsolidationTracker(window_turns=10)
    tracker.recall("FalkorDB")
    assert tracker.is_active("FalkorDB")


def test_activation_expires_after_window():
    """Activation should expire after the reconsolidation window (turns)."""
    tracker = ReconsolidationTracker(window_turns=2)
    tracker.recall("Docker")
    assert tracker.is_active("Docker")  # turn 0
    tracker.tick()  # turn 1
    assert tracker.is_active("Docker")  # still active
    tracker.tick()  # turn 2
    assert not tracker.is_active("Docker")  # expired


def test_unknown_entity_not_active():
    """An entity that was never recalled should not be active."""
    tracker = ReconsolidationTracker(window_turns=10)
    assert not tracker.is_active("UnknownEntity")
    assert tracker.get_recall_count("UnknownEntity") == 0


def test_reconsolidation_boost():
    """Active entities should get a salience boost, expired ones should not."""
    tracker = ReconsolidationTracker(window_turns=2, boost=0.2)
    boost = tracker.get_boost("NeverSeen")  # not recalled
    assert boost == 0.0

    tracker.recall("Synapse")
    boost = tracker.get_boost("Synapse")  # recalled and active
    assert boost == 0.2

    tracker.tick()
    assert tracker.is_active("Synapse")  # 1 < 2, still active
    tracker.tick()
    assert not tracker.is_active("Synapse")  # 2 < 2 = False, expired
    boost = tracker.get_boost("Synapse")
    assert boost == 0.0


def test_multiple_entities_tracked():
    """Multiple entities should be tracked independently."""
    tracker = ReconsolidationTracker(window_turns=10)
    tracker.recall("A")
    tracker.recall("B")
    tracker.recall("B")
    assert tracker.get_recall_count("A") == 1
    assert tracker.get_recall_count("B") == 2
    assert tracker.is_active("A")
    assert tracker.is_active("B")


def test_get_active_entities():
    """Should return all currently active entities."""
    tracker = ReconsolidationTracker(window_turns=10)
    tracker.recall("A")
    tracker.recall("B")
    active = tracker.get_active_entities()
    assert "A" in active
    assert "B" in active
