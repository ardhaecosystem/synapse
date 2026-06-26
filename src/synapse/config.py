"""Synapse configuration — all optimization parameters in one place."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class SynapseConfig:
    """Configuration for Synapse memory provider.

    All optimization parameters have sensible defaults validated during spikes.
    Override via environment variables (SYNAPSE_*) or directly.
    """

    # FalkorDB connection
    falkordb_host: str = "localhost"
    falkordb_port: int = 6379
    falkordb_password: str | None = None
    falkordb_database: str = "synapse"

    # LLM config (OpenAI-compatible endpoint)
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    # Optimization parameters (validated in spikes)
    batch_size: int = 5                    # turns per episode (−86% LLM calls)
    half_life_days: float = 7.0            # forgetting curve base
    salience_boost: float = 3.0            # high-salience decay multiplier
    recall_boost: float = 1.5              # recall strengthening factor
    prune_threshold: float = 0.05          # below = prune
    trivial_turn_threshold: int = 10       # chars; below = skip turn
    prefetch_mode: str = "bm25"            # "bm25" (fast) or "reranker" (accurate)
    tool_name: str = "synapse_query"       # merged tool name

    # Consolidation
    consolidation_interval_hours: float = 6.0

    @classmethod
    def from_env(cls) -> SynapseConfig:
        """Create config from environment variables (SYNAPSE_* prefix)."""
        return cls(
            falkordb_host=os.environ.get("SYNAPSE_FALKORDB_HOST", "localhost"),
            falkordb_port=int(os.environ.get("SYNAPSE_FALKORDB_PORT", "6379")),
            falkordb_password=os.environ.get("SYNAPSE_FALKORDB_PASSWORD"),
            falkordb_database=os.environ.get("SYNAPSE_DATABASE", "synapse"),
            llm_api_key=os.environ.get("SYNAPSE_LLM_API_KEY", ""),
            llm_base_url=os.environ.get("SYNAPSE_LLM_BASE_URL", ""),
            llm_model=os.environ.get("SYNAPSE_LLM_MODEL", "gpt-4o-mini"),
            embedding_model=os.environ.get("SYNAPSE_EMBEDDING_MODEL", "text-embedding-3-small"),
            batch_size=int(os.environ.get("SYNAPSE_BATCH_SIZE", "5")),
            half_life_days=float(os.environ.get("SYNAPSE_HALF_LIFE_DAYS", "7.0")),
        )
