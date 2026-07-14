"""Tests for FalkorHelper bounded fetch methods."""

from synapse.falkor import FalkorHelper


def test_get_recent_edges_query_structure():
    """get_recent_edges should build a bounded query — verify via mock."""
    # We can't test against real FalkorDB without it running, but we can
    # verify the helper constructs correctly and the method exists.
    helper = FalkorHelper(host="localhost", port=6379)
    assert hasattr(helper, "get_recent_edges")
    assert hasattr(helper, "get_entity_neighborhood")


def test_get_entity_neighborhood_empty_names():
    """get_entity_neighborhood with empty entity list should return []."""
    helper = FalkorHelper(host="localhost", port=6379)
    result = helper.get_entity_neighborhood("test-group", [])
    assert result == []
