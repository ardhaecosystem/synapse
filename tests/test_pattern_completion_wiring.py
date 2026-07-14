"""Tests for pattern completion wiring in synapse_query handler."""

import json

from synapse.provider import SynapseMemoryProvider


def test_query_with_pattern_completion():
    """synapse_query should expand results via pattern completion."""
    p = SynapseMemoryProvider()
    p._initialized = True

    class MockRetrieval:
        def search(self, query, limit=5):
            return [
                {"from_node": "A", "fact": "A uses B", "to_node": "B",
                 "valid_at": "2026-07-14T00:00:00Z", "invalid_at": None},
            ]

        def temporal_search(self, query, at_time, limit=20):
            return []

    p._retrieval = MockRetrieval()

    class MockHippocampus:
        def __init__(self):
            self.recalled = []

        def on_recall(self, entities, edges=None):
            self.recalled.extend(entities)

        def expand_recall(self, query, edges):
            return {
                "facts": [
                    {"from_node": "B", "fact": "B runs in Docker",
                     "to_node": "Docker", "valid_at": "2026-01-01T00:00:00Z",
                     "invalid_at": None},
                ],
                "entities": ["A", "B", "Docker"],
                "depth": 1,
            }

        def get_rif_penalty(self, entity):
            return 0.0

    p._hippocampus = MockHippocampus()

    class MockConfig:
        falkordb_host = "localhost"
        falkordb_port = 6379
        falkordb_password = None

    p._config = MockConfig()

    class MockFalkorHelper:
        def __init__(self, **kwargs):
            pass

        def get_entity_neighborhood(self, group_id, entities, depth=1, limit=20):
            return [
                {"from_node": "B", "fact": "B runs in Docker",
                 "to_node": "Docker", "valid_at": "2026-01-01T00:00:00Z",
                 "invalid_at": None},
            ]

    import synapse.falkor as falkor_mod
    original_get = falkor_mod.FalkorHelper
    falkor_mod.FalkorHelper = MockFalkorHelper

    try:
        result = json.loads(p.handle_tool_call(
            "synapse_query", {"query": "A uses B"}
        ))
    finally:
        falkor_mod.FalkorHelper = original_get

    assert len(result["results"]) >= 1
    facts = [r.get("fact", "") for r in result["results"]]
    assert "A uses B" in facts
    assert "pattern_completion" in result
    assert "B runs in Docker" in facts

    assert "A" in p._hippocampus.recalled
    assert "B" in p._hippocampus.recalled


def test_query_pattern_completion_no_entities():
    """synapse_query with no results should not trigger pattern completion."""
    p = SynapseMemoryProvider()
    p._initialized = True

    class MockRetrieval:
        def search(self, query, limit=5):
            return []

        def temporal_search(self, query, at_time, limit=20):
            return []

    p._retrieval = MockRetrieval()

    class MockHippocampus:
        def __init__(self):
            self.recalled = []

        def on_recall(self, entities, edges=None):
            self.recalled.extend(entities)

        def expand_recall(self, query, edges):
            return {"facts": [], "entities": [], "depth": 0}

        def get_rif_penalty(self, entity):
            return 0.0

    p._hippocampus = MockHippocampus()

    result = json.loads(p.handle_tool_call(
        "synapse_query", {"query": "nonexistent"}
    ))
    assert result["count"] == 0
    assert p._hippocampus.recalled == []
