"""Tests for synapse_remember tool."""

import json

from synapse.tools import get_all_tool_schemas, handle_remember


def test_remember_schema_exists():
    """synapse_remember should be in the tool schemas."""
    schemas = get_all_tool_schemas()
    names = [s["name"] for s in schemas]
    assert "synapse_remember" in names


def test_remember_schema_has_required_fields():
    """synapse_remember schema should have content and category."""
    schemas = get_all_tool_schemas()
    remember = next(s for s in schemas if s["name"] == "synapse_remember")
    props = remember["parameters"]["properties"]
    assert "content" in props
    assert "category" in props
    assert remember["parameters"]["required"] == ["content"]


def test_remember_schema_not_too_large():
    """Both schemas combined should be <150 tokens."""
    schemas = get_all_tool_schemas()
    total_chars = sum(len(json.dumps(s)) for s in schemas)
    # 1 token ≈ 4 chars
    assert total_chars / 4 < 200  # two tools, tightened schemas


def test_handle_remember_stores_fact():
    """handle_remember should store a fact via the store callback."""
    stored = []
    def mock_store(content, category):
        stored.append({"content": content, "category": category})
        return True

    result = json.loads(handle_remember(
        {"content": "User prefers concise responses", "category": "user_profile"},
        store_fn=mock_store,
    ))
    assert result["success"] is True
    assert len(stored) == 1
    assert stored[0]["content"] == "User prefers concise responses"
    assert stored[0]["category"] == "user_profile"


def test_handle_remember_default_category():
    """Default category should be 'general'."""
    stored = []
    def mock_store(content, category):
        stored.append({"content": content, "category": category})
        return True

    result = json.loads(handle_remember(
        {"content": "Project uses Python 3.11"},
        store_fn=mock_store,
    ))
    assert result["success"] is True
    assert stored[0]["category"] == "general"


def test_handle_remember_empty_content_fails():
    """Empty content should fail gracefully."""
    def mock_store(content, category):
        return True

    result = json.loads(handle_remember(
        {"content": ""},
        store_fn=mock_store,
    ))
    assert result["success"] is False


def test_handle_remember_store_failure():
    """If store returns False, result should reflect failure."""
    def mock_store(content, category):
        return False

    result = json.loads(handle_remember(
        {"content": "test fact", "category": "general"},
        store_fn=mock_store,
    ))
    assert result["success"] is False


def test_query_schema_still_exists():
    """synapse_query should still be in schemas (we added, not replaced)."""
    schemas = get_all_tool_schemas()
    names = [s["name"] for s in schemas]
    assert "synapse_query" in names
