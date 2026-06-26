"""Tests for SynapseMemoryProvider."""

import json
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

    for key in ["SYNAPSE_FALKORDB_HOST", "SYNAPSE_LLM_API_KEY", "SYNAPSE_LLM_BASE_URL"]:
        os.environ.pop(key, None)


def test_system_prompt_brain_mode_when_native_disabled():
    """When native memory is disabled, system prompt should be brain-mode."""
    p = SynapseMemoryProvider()
    p._initialized = True
    p._native_memory_active = False
    block = p.system_prompt_block()
    assert "synapse_remember" in block
    assert "synapse_query" in block
    assert "temporal knowledge graph" in block


def test_system_prompt_minimal_when_native_active():
    """When native memory is active, system prompt should be minimal."""
    p = SynapseMemoryProvider()
    p._initialized = True
    p._native_memory_active = True
    block = p.system_prompt_block()
    assert "synapse_query" in block
    assert "synapse_remember" not in block  # minimal mode


def test_system_prompt_includes_user_profile_facts():
    """Brain-mode prompt should include cached user_profile facts."""
    p = SynapseMemoryProvider()
    p._initialized = True
    p._native_memory_active = False
    p._remembered_facts = [
        {"content": "User prefers concise responses", "category": "user_profile"},
        {"content": "Project uses Python 3.11", "category": "environment"},
    ]
    block = p.system_prompt_block()
    assert "User prefers concise responses" in block
    assert "Project uses Python 3.11" in block
    assert "What you know about your user" in block
    assert "What you know about your environment" in block


def test_system_prompt_empty_when_not_initialized():
    """System prompt should be empty before initialization."""
    p = SynapseMemoryProvider()
    assert p.system_prompt_block() == ""


def test_tool_schemas_include_both_tools():
    """Provider should expose both synapse_query and synapse_remember."""
    p = SynapseMemoryProvider()
    schemas = p.get_tool_schemas()
    names = [s["name"] for s in schemas]
    assert "synapse_query" in names
    assert "synapse_remember" in names
    assert len(schemas) == 2


def test_handle_remember_via_provider():
    """Provider should route synapse_remember to _store_remembered_fact."""
    p = SynapseMemoryProvider()
    result = json.loads(p.handle_tool_call(
        "synapse_remember",
        {"content": "User likes dark mode", "category": "user_profile"},
    ))
    assert result["success"] is True
    assert result["category"] == "user_profile"
    # Fact should be cached
    assert len(p._remembered_facts) == 1
    assert p._remembered_facts[0]["content"] == "User likes dark mode"


def test_on_memory_write_sets_native_flag():
    """on_memory_write should set _native_memory_active to True."""
    p = SynapseMemoryProvider()
    p._initialized = True
    assert not p._native_memory_active

    p.on_memory_write("add", "memory", "test fact")
    assert p._native_memory_active is True


def test_native_flag_changes_prompt_mode():
    """After on_memory_write fires, prompt should switch to minimal mode."""
    p = SynapseMemoryProvider()
    p._initialized = True
    p._native_memory_active = False

    # Brain mode
    block_before = p.system_prompt_block()
    assert "synapse_remember" in block_before

    # Native memory fires → switch to supplementary mode
    p.on_memory_write("add", "memory", "test fact")

    block_after = p.system_prompt_block()
    assert "synapse_remember" not in block_after


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
