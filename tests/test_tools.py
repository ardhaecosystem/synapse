"""Tests for synapse_query tool."""

import json

from synapse.tools import get_tool_schema, handle_tool_call


def test_single_tool_schema():
    schema = get_tool_schema()
    assert schema["name"] == "synapse_query"
    assert "query" in schema["parameters"]["properties"]
    assert "at_time" in schema["parameters"]["properties"]
    assert schema["parameters"]["required"] == ["query"]


def test_schema_token_efficiency():
    """Merged schema should be <100 tokens."""
    schema = get_tool_schema()
    schema_str = json.dumps(schema)
    # 1 token ≈ 4 chars
    assert len(schema_str) / 4 < 100


def test_handle_tool_call_search():
    """handle_tool_call should dispatch to retrieval engine."""
    class MockRetrieval:
        def search(self, query, limit=5):
            return [{"fact": "test fact", "from_node": "A", "to_node": "B"}]
        def temporal_search(self, query, at_time, limit=20):
            return [{"fact": "old fact", "from_node": "A", "to_node": "B"}]

    result = json.loads(handle_tool_call({"query": "test"}, MockRetrieval()))
    assert result["count"] == 1
    assert result["results"][0]["fact"] == "test fact"


def test_handle_tool_call_temporal():
    """handle_tool_call with at_time should use temporal_search."""
    class MockRetrieval:
        def search(self, query, limit=5):
            return []
        def temporal_search(self, query, at_time, limit=20):
            return [{"fact": f"fact at {at_time}"}]

    result = json.loads(handle_tool_call(
        {"query": "test", "at_time": "2026-06-22"}, MockRetrieval()
    ))
    assert result["count"] == 1
    assert "2026-06-22" in result["results"][0]["fact"]
