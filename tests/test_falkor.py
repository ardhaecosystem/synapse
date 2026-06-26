"""Tests for FalkorHelper."""

from synapse.falkor import FalkorHelper


def test_temporal_filter_query():
    """The substring() workaround produces correct temporal filtering."""
    helper = FalkorHelper(host="localhost", port=6379)
    query = helper.temporal_filter_query(
        valid_at_max="2026-06-22",
        include_invalid=False,
    )
    # Should use substring() on valid_at (the FalkorDB <= bug workaround)
    assert "substring(r.valid_at, 0, 10)" in query
    assert "<=" in query
    # Should exclude invalidated edges
    assert "r.invalid_at IS NULL" in query


def test_temporal_filter_with_include_invalid():
    """When include_invalid=True, don't filter out invalidated edges."""
    helper = FalkorHelper(host="localhost", port=6379)
    query = helper.temporal_filter_query(
        valid_at_max="2026-06-22",
        include_invalid=True,
    )
    assert "substring(r.valid_at, 0, 10)" in query
    # Should NOT have the invalid_at filter
    assert "r.invalid_at IS NULL" not in query


def test_temporal_filter_limit():
    """Query should have a LIMIT clause."""
    helper = FalkorHelper(host="localhost", port=6379)
    query = helper.temporal_filter_query(valid_at_max="2026-06-22", limit=50)
    assert "LIMIT 50" in query
