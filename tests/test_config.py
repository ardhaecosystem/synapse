"""Tests for SynapseConfig."""

import os

from synapse.config import SynapseConfig


def test_default_config():
    config = SynapseConfig()
    assert config.falkordb_host == "localhost"
    assert config.falkordb_port == 6379
    assert config.batch_size == 5
    assert config.half_life_days == 7.0
    assert config.salience_boost == 3.0
    assert config.prune_threshold == 0.05
    assert config.trivial_turn_threshold == 10
    assert config.prefetch_mode == "bm25"
    assert config.tool_name == "synapse_query"


def test_config_from_env():
    os.environ["SYNAPSE_FALKORDB_HOST"] = "remote.host"
    os.environ["SYNAPSE_BATCH_SIZE"] = "10"
    try:
        config = SynapseConfig.from_env()
        assert config.falkordb_host == "remote.host"
        assert config.batch_size == 10
    finally:
        del os.environ["SYNAPSE_FALKORDB_HOST"]
        del os.environ["SYNAPSE_BATCH_SIZE"]


def test_config_llm_defaults():
    config = SynapseConfig()
    assert config.llm_model == "gpt-4o-mini"
    assert config.embedding_model == "text-embedding-3-small"
