"""Tests for SynapseMemoryProvider."""

import os

from synapse.provider import SynapseMemoryProvider


def test_provider_name():
    p = SynapseMemoryProvider()
    assert p.name == "synapse"


def test_is_available_requires_env():
    for key in ["SYNAPSE_FALKORDB_HOST", "SYNAPSE_LLM_API_KEY", "SYNAPSE_LLM_BASE_URL"]:
        os.environ.pop(key, None)
    p = SynapseMemoryProvider()
    assert not p.is_available()

    os.environ["SYNAPSE_FALKORDB_HOST"] = "localhost"
    os.environ["SYNAPSE_LLM_API_KEY"] = "test-key"
    os.environ["SYNAPSE_LLM_BASE_URL"] = "https://api.test.com"
    assert p.is_available()

    # Cleanup
    for key in ["SYNAPSE_FALKORDB_HOST", "SYNAPSE_LLM_API_KEY", "SYNAPSE_LLM_BASE_URL"]:
        os.environ.pop(key, None)


def test_system_prompt_is_minimal():
    p = SynapseMemoryProvider()
    block = p.system_prompt_block()
    # Should be <80 chars (15 tokens) — optimization #4
    assert len(block) < 80


def test_tool_schemas_single_tool():
    p = SynapseMemoryProvider()
    schemas = p.get_tool_schemas()
    assert len(schemas) == 1  # merged tool, not 2
    assert schemas[0]["name"] == "synapse_query"


def test_config_schema_has_required_fields():
    p = SynapseMemoryProvider()
    config_fields = p.get_config_schema()
    field_keys = [f["key"] for f in config_fields]
    assert "falkordb_host" in field_keys
    assert "llm_api_key" in field_keys
    assert "batch_size" in field_keys
    assert "half_life_days" in field_keys


def test_backup_paths_empty():
    """FalkorDB data is in Docker — no external paths to declare."""
    p = SynapseMemoryProvider()
    assert p.backup_paths() == []
